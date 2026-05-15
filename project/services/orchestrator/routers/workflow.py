from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from services.orchestrator.services.workflow_engine import WorkflowEngine, WorkflowStatus
from services.orchestrator.services import tasks as task_service

router = APIRouter(prefix="/api/v1")

_executions: dict[str, dict] = {}


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
    execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    task_id = execution["task_id"]
    engine = WorkflowEngine(db)
    success = await engine.cancel_workflow(UUID(task_id))

    if success:
        execution["status"] = WorkflowStatus.CANCELLED.value
        return {"status": "cancelled", "execution_id": execution_id}
    raise HTTPException(status_code=400, detail="Cannot cancel this execution")


@router.post("/workflows/{execution_id}/retry")
async def retry_execution(
    execution_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    task_id = execution["task_id"]
    execution["status"] = WorkflowStatus.RUNNING.value
    execution["result"] = None

    background_tasks.add_task(_run_workflow_task, execution_id, UUID(task_id))

    return {"status": "retrying", "execution_id": execution_id}


async def _run_workflow_task(execution_id: str, task_id: UUID):
    from shared.database import async_session_factory

    async with async_session_factory() as db:
        try:
            engine = WorkflowEngine(db)
            result = await engine.run_workflow(task_id)
            _executions[execution_id]["result"] = result
            _executions[execution_id]["status"] = result.status.value
        except Exception as e:
            _executions[execution_id]["status"] = WorkflowStatus.FAILED.value
            _executions[execution_id]["error"] = str(e)
