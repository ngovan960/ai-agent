import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.orchestrator.services.audit_service import create_audit_log
from services.orchestrator.services.retry_service import should_escalate
from shared.config.state_transitions import validate_transition
from shared.models.task import Task, TaskDependency, TaskOutput
from shared.schemas.task import StateTransitionRequest, TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


async def get_tasks(
    db: AsyncSession,
    project_id: UUID | None = None,
    module_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    priority: str | None = None,
) -> tuple[list[Task], int]:
    query = select(Task)
    count_query = select(func.count()).select_from(Task)

    if project_id:
        query = query.where(Task.project_id == project_id)
        count_query = count_query.where(Task.project_id == project_id)
    if module_id:
        query = query.where(Task.module_id == module_id)
        count_query = count_query.where(Task.module_id == module_id)
    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size).order_by(Task.created_at.desc())
    )
    return result.scalars().all(), total


async def get_task(db: AsyncSession, task_id: UUID, project_id: UUID | None = None) -> Task | None:
    query = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.dependencies),
            selectinload(Task.outputs),
            selectinload(Task.retry_records),
        )
    )
    if project_id:
        query = query.where(Task.project_id == project_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    task = Task(**data.model_dump())
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task_id: UUID, data: TaskUpdate) -> Task | None:
    task = await get_task(db, task_id)
    if not task:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: UUID) -> bool:
    task = await get_task(db, task_id)
    if not task:
        return False
    await db.delete(task)
    await db.flush()
    return True


async def transition_task_state(
    db: AsyncSession, task_id: UUID, request: StateTransitionRequest
) -> tuple[Task | None, str | None]:
    task = await get_task(db, task_id)
    if not task:
        return None, "Task not found"

    current_status = task.status.value if hasattr(task.status, "value") else task.status
    target_status = request.target_status.value if hasattr(request.target_status, "value") else request.target_status

    is_valid, error = validate_transition(current_status, target_status)
    if not is_valid:
        return None, error

    # Pre-hook: auto-escalate if max retries exceeded
    if target_status in ("IMPLEMENTING", "VERIFYING"):
        escalated = await should_escalate(db, task_id)
        if escalated:
            task.retries = (task.retries or 0) + 1
            await create_audit_log(db, task_id, "pre_transition_escalate", "system", "system",
                                   input_data={"from": current_status, "to": target_status},
                                   output_data={"escalated": True, "retries": task.retries},
                                   message=f"Auto-escalated: max retries hit at {current_status}")

    task.status = request.target_status

    now = datetime.now(UTC)
    if target_status == "DONE":
        task.completed_at = now
        # Post-hook: resolve dependent tasks
        await _unblock_dependents(db, task_id)
    elif target_status == "FAILED":
        task.failed_at = now
        if request.reason:
            task.failure_reason = request.reason
    elif target_status == "CANCELLED":
        task.cancelled_at = now
        if request.reason:
            task.cancellation_reason = request.reason

    await db.flush()
    await db.refresh(task)

    # Post-hook: audit log
    await create_audit_log(db, task_id, "state_transition", "system", "system",
                           input_data={"from": current_status, "to": target_status, "reason": request.reason},
                           result="SUCCESS",
                           message=f"Transition: {current_status} → {target_status}")
    return task, None


async def _unblock_dependents(db: AsyncSession, task_id: UUID) -> None:
    try:
        result = await db.execute(
            select(TaskDependency).where(TaskDependency.depends_on_task_id == task_id)
        )
        deps = result.scalars().all()
        for dep in deps:
            blocked_task = await db.get(Task, dep.task_id)
            if blocked_task and blocked_task.status.value == "BLOCKED":
                await transition_task_state(db, dep.task_id,
                    StateTransitionRequest(target_status="PLANNING", reason="Dependency resolved: parent task DONE"))
    except Exception as e:
        logger.warning(f"Failed to unblock dependents for task {task_id}: {e}")


async def add_task_dependency(
    db: AsyncSession, task_id: UUID, depends_on_task_id: UUID, dependency_type: str = "blocks"
) -> TaskDependency | None:
    if task_id == depends_on_task_id:
        return None

    existing = await db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    dep = TaskDependency(
        task_id=task_id,
        depends_on_task_id=depends_on_task_id,
        dependency_type=dependency_type,
    )
    db.add(dep)
    await db.flush()
    await db.refresh(dep)
    
    from services.orchestrator.services.dependency_service import clear_dependency_cache
    clear_dependency_cache()
    
    return dep


async def remove_task_dependency(db: AsyncSession, dep_id: UUID) -> bool:
    result = await db.execute(select(TaskDependency).where(TaskDependency.id == dep_id))
    dep = result.scalar_one_or_none()
    if not dep:
        return False
    await db.delete(dep)
    await db.flush()
    
    from services.orchestrator.services.dependency_service import clear_dependency_cache
    clear_dependency_cache()
    
    return True


async def create_task_output(
    db: AsyncSession, task_id: UUID, output_type: str, content: dict
) -> TaskOutput | None:
    task = await get_task(db, task_id)
    if not task:
        return None

    output = TaskOutput(task_id=task_id, output_type=output_type, content=content)
    db.add(output)
    await db.flush()
    await db.refresh(output)
    return output
