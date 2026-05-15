import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from services.orchestrator.services.workflow_engine import WorkflowEngine, WorkflowStatus
from services.orchestrator.services import tasks as task_service
from services.orchestrator.services import escalation_service
from services.orchestrator.services import mentor_service

router = APIRouter(prefix="/api/v1")

_executions: dict[str, dict] = {}
_executions_lock = asyncio.Lock()


class ExecuteTaskRequest(BaseModel):
    mode: str = Field(default="dev", description="Execution mode: dev or prod")
    timeout: int = Field(default=600, ge=30, le=3600)
    force_agent: str | None = None


class ExecuteTaskResponse(BaseModel):
    execution_id: str
    task_id: str
    status: str
    message: str


class ExecutionStatus(BaseModel):
    execution_id: str
    task_id: str
    status: str
    current_state: str | None = None
    nodes_completed: int = 0
    total_cost_usd: float = 0.0
    error: str | None = None


@router.post("/tasks/{task_id}/execute", response_model=ExecuteTaskResponse, status_code=202)
async def execute_task(
    task_id: UUID,
    request: ExecuteTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import uuid
    execution_id = str(uuid.uuid4())

    async with _executions_lock:
        _executions[execution_id] = {
            "task_id": str(task_id),
            "status": WorkflowStatus.RUNNING.value,
            "started_at": None,
            "result": None,
        }

    background_tasks.add_task(_run_workflow_task, execution_id, task_id)

    return ExecuteTaskResponse(
        execution_id=execution_id,
        task_id=str(task_id),
        status=WorkflowStatus.RUNNING.value,
        message=f"Workflow started for task {task_id}",
    )


@router.get("/workflows/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
    async with _executions_lock:
        execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    result = execution.get("result")
    nodes_completed = len(result.nodes) if result else 0
    total_cost = result.total_cost_usd if result else 0
    current_state = None
    if result and result.nodes:
        current_state = result.nodes[-1].output_state or result.nodes[-1].input_state

    return ExecutionStatus(
        execution_id=execution_id,
        task_id=execution["task_id"],
        status=execution["status"],
        current_state=current_state,
        nodes_completed=nodes_completed,
        total_cost_usd=total_cost,
        error=result.error if result else None,
    )


@router.post("/workflows/{execution_id}/cancel")
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    async with _executions_lock:
        execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    task_id = execution["task_id"]
    engine = WorkflowEngine(db)
    success = await engine.cancel_workflow(UUID(task_id))

    if success:
        async with _executions_lock:
            execution["status"] = WorkflowStatus.CANCELLED.value
        return {"status": "cancelled", "execution_id": execution_id}
    raise HTTPException(status_code=400, detail="Cannot cancel this execution")


@router.post("/workflows/{execution_id}/retry")
async def retry_execution(
    execution_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    async with _executions_lock:
        execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    task_id = execution["task_id"]
    async with _executions_lock:
        execution["status"] = WorkflowStatus.RUNNING.value
        execution["result"] = None

    background_tasks.add_task(_run_workflow_task, execution_id, UUID(task_id))

    return {"status": "retrying", "execution_id": execution_id}


@router.post("/tasks/{task_id}/escalate")
async def escalate_task_endpoint(
    task_id: UUID,
    reason: str,
    context: dict | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Escalate a task and add it to the priority queue."""
    success, message = await escalation_service.escalate_task(db, task_id, reason, context)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"task_id": str(task_id), "status": "escalated", "message": message}


@router.get("/escalations/queue")
async def get_escalation_queue():
    """Get the escalation priority queue."""
    queue = escalation_service.get_escalation_queue()
    items = queue.get_all()
    return {
        "queue_size": len(items),
        "items": [
            {
                "task_id": str(i.task_id),
                "title": i.task_title,
                "risk_level": i.risk_level,
                "retries": i.retries,
                "reason": i.reason,
            }
            for i in items
        ],
    }


@router.get("/escalations/stats")
async def get_escalation_stats(db: AsyncSession = Depends(get_db)):
    """Get escalation statistics."""
    return await escalation_service.get_escalation_stats(db)


@router.post("/tasks/{task_id}/takeover")
async def mentor_takeover_endpoint(
    task_id: UUID,
    mentor_id: str,
    action: str,
    reason: str,
    new_instructions: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mentor takeover an escalated task."""
    from services.orchestrator.services.mentor_service import MentorAction

    try:
        mentor_action = MentorAction(action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}. Must be one of: rewrite, redesign, override, reject, approve")

    can_call, remaining, limit = await mentor_service.check_mentor_quota(db)
    if not can_call:
        raise HTTPException(status_code=429, detail=f"Mentor quota exceeded ({limit} calls/day)")

    success, message, result = await mentor_service.mentor_takeover(
        db, task_id, mentor_id, mentor_action, reason, new_instructions,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)

    await mentor_service.record_mentor_call(db)
    return {"task_id": str(task_id), "status": "taken_over", "message": message, "result": result}


@router.get("/tasks/{task_id}/mentor-instructions")
async def get_mentor_instructions(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all mentor instructions for a task."""
    instructions = await mentor_service.get_mentor_instructions(db, task_id)
    return {"task_id": str(task_id), "instructions": instructions, "total": len(instructions)}


async def _run_workflow_task(execution_id: str, task_id: UUID):
    from shared.database import async_session_factory

    async with async_session_factory() as db:
        try:
            engine = WorkflowEngine(db)
            result = await engine.run_workflow(task_id)
            async with _executions_lock:
                _executions[execution_id]["result"] = result
                _executions[execution_id]["status"] = result.status.value
        except Exception as e:
            async with _executions_lock:
                _executions[execution_id]["status"] = WorkflowStatus.FAILED.value
                _executions[execution_id]["error"] = str(e)
