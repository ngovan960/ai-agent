from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services import audit_service, retry_service
from services.orchestrator.services import tasks as task_service
from services.orchestrator.services.dependency_service import check_circular
from services.orchestrator.services.risk_classifier import RiskClassifier
from shared.database import get_db
from shared.schemas.audit import AuditLogListResponse, AuditLogResponse
from shared.schemas.retry import RetryCreate, RetryListResponse, RetryResponse
from shared.schemas.task import (
    StateTransitionRequest,
    TaskCreate,
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskListResponse,
    TaskOutputCreate,
    TaskOutputResponse,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter()
_risk_classifier = RiskClassifier()


async def _trigger_workflow(task_id: UUID):
    try:
        from services.orchestrator.services.workflow_engine import WorkflowEngine
        from shared.database import async_session_factory
        async with async_session_factory() as session:
            engine = WorkflowEngine(session)
            result = await engine.run_workflow(task_id)
            if result.status.value == "failed":
                from shared.cache import get_redis
                try:
                    import json
                    r = await get_redis()
                    event = json.dumps({"task_id": str(task_id), "status": "failed", "error": result.error or ""})
                    await r.publish("workflow:events", event)
                except Exception:
                    pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Workflow trigger failed for task {task_id}: {e}", exc_info=True)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
    module_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
):
    items, total = await task_service.get_tasks(db, project_id, module_id, page, page_size, status, priority)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db), background_tasks: BackgroundTasks = None):
    task = await task_service.create_task(db, data)

    risk = _risk_classifier.classify(
        task_id=task.id,
        complexity=5,
        data_sensitivity=0,
        user_impact=0,
        deployment_scope=0,
    )
    task.risk_score = risk.risk_score
    from shared.models.task import RiskLevel
    task.risk_level = RiskLevel(risk.risk_level)
    await db.flush()
    await db.refresh(task)

    if background_tasks:
        background_tasks.add_task(_trigger_workflow, task.id)

    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await task_service.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/transition", response_model=TaskResponse)
async def transition_task(
    task_id: UUID, request: StateTransitionRequest, db: AsyncSession = Depends(get_db)
):
    task, error = await task_service.transition_task_state(db, task_id, request)
    if error:
        raise HTTPException(status_code=400 if "not found" not in error.lower() else 404, detail=error)
    try:
        from services.orchestrator.routers.dashboard import broadcast
        await broadcast({
            "type": "task_transition",
            "task_id": str(task_id),
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "timestamp": datetime.now(UTC).isoformat(),
        })
    except Exception:
        pass
    return TaskResponse.model_validate(task)


@router.post("/dependencies", response_model=TaskDependencyResponse, status_code=201)
async def add_dependency(data: TaskDependencyCreate, db: AsyncSession = Depends(get_db)):
    circular = await check_circular(db, data.task_id, data.depends_on_task_id)
    if circular:
        raise HTTPException(status_code=400, detail="Circular dependency detected")
    dep = await task_service.add_task_dependency(
        db, data.task_id, data.depends_on_task_id, data.dependency_type
    )
    if not dep:
        raise HTTPException(status_code=400, detail="Invalid or duplicate dependency")
    return TaskDependencyResponse.model_validate(dep)


@router.delete("/dependencies/{dep_id}", status_code=204)
async def remove_dependency(dep_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.remove_task_dependency(db, dep_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")


@router.post("/{task_id}/retry", response_model=RetryResponse, status_code=201)
async def retry_task(task_id: UUID, data: RetryCreate, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    record, error = await retry_service.create_retry(db, task_id, data.reason, data.agent_name, data.error_log)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return RetryResponse.model_validate(record)


@router.get("/{task_id}/retries", response_model=RetryListResponse)
async def list_retries(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await retry_service.get_retries(db, task_id, page, page_size)
    return RetryListResponse(
        items=[RetryResponse.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{task_id}/audit-logs", response_model=AuditLogListResponse)
async def list_task_audit_logs(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await audit_service.get_audit_logs(db, task_id, page, page_size)
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(a) for a in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/outputs", response_model=TaskOutputResponse, status_code=201)
async def create_output(data: TaskOutputCreate, db: AsyncSession = Depends(get_db)):
    output = await task_service.create_task_output(db, data.task_id, data.output_type, data.content)
    if not output:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOutputResponse.model_validate(output)
