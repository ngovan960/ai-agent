from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.task import Task, TaskDependency, TaskOutput
from shared.schemas.task import TaskCreate, TaskUpdate, StateTransitionRequest
from shared.config.state_transitions import validate_transition
from shared.concurrency import OptimisticLockError


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


async def get_task(db: AsyncSession, task_id: UUID) -> Task | None:
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.dependencies),
            selectinload(Task.outputs),
            selectinload(Task.retry_records),
        )
    )
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    task = Task(**data.model_dump())
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


UPDATABLE_TASK_FIELDS = {
    "title", "description", "owner", "priority", "confidence",
    "expected_output", "risk_score", "risk_level",
    "cancellation_reason", "failure_reason",
}


async def update_task(db: AsyncSession, task_id: UUID, data: TaskUpdate) -> Task | None:
    task = await get_task(db, task_id)
    if not task:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in UPDATABLE_TASK_FIELDS:
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
    db: AsyncSession, task_id: UUID, request: StateTransitionRequest, expected_version: int | None = None
) -> tuple[Task | None, str | None]:
    """
    Transition task state with optimistic locking.

    Args:
        db: Async database session
        task_id: Task UUID
        request: State transition request with target_status and reason
        expected_version: Expected version for optimistic locking (optional)

    Returns:
        Tuple of (updated_task, error_message)

    Raises:
        OptimisticLockError: If version mismatch detected (concurrent update)
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id).with_for_update()
    )
    task = result.scalar_one_or_none()
    if not task:
        return None, "Task not found"

    if expected_version is not None and task.version != expected_version:
        raise OptimisticLockError(
            f"Task {task_id} was modified by another process "
            f"(expected version {expected_version}, got {task.version})"
        )

    current_status = task.status.value if hasattr(task.status, "value") else task.status
    target_status = request.target_status.value if hasattr(request.target_status, "value") else request.target_status

    is_valid, error = validate_transition(current_status, target_status)
    if not is_valid:
        return None, error

    task.status = request.target_status
    task.version += 1

    now = datetime.now(timezone.utc)
    if target_status == "DONE":
        task.completed_at = now
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
    return task, None


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
    return dep


async def remove_task_dependency(db: AsyncSession, dep_id: UUID) -> bool:
    result = await db.execute(select(TaskDependency).where(TaskDependency.id == dep_id))
    dep = result.scalar_one_or_none()
    if not dep:
        return False
    await db.delete(dep)
    await db.flush()
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
