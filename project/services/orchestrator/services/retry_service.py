import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import Retry

logger = logging.getLogger(__name__)

MAX_RETRIES_DEFAULT = 2
MAX_RETRIES = MAX_RETRIES_DEFAULT


async def get_retries(db: AsyncSession, task_id: UUID, page: int = 1, page_size: int = 20):
    query = select(Retry).where(Retry.task_id == task_id).order_by(Retry.attempt_number.desc())
    count_q = select(func.count()).select_from(Retry).where(Retry.task_id == task_id)
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def create_retry(db: AsyncSession, task_id: UUID, reason: str, agent_name: str = "", error_log: str = "", max_retries: int | None = None):
    effective_max = max_retries if max_retries is not None else MAX_RETRIES_DEFAULT
    count_q = select(func.count()).select_from(Retry).where(Retry.task_id == task_id)
    attempt = (await db.execute(count_q)).scalar() + 1
    if attempt > effective_max:
        return None, f"Max retries ({effective_max}) exceeded"
    record = Retry(task_id=task_id, attempt_number=attempt, reason=reason, agent_name=agent_name, error_log=error_log)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record, None


async def get_retry_count(db: AsyncSession, task_id: UUID) -> int:
    count_q = select(func.count()).select_from(Retry).where(Retry.task_id == task_id)
    return (await db.execute(count_q)).scalar()


async def should_escalate(db: AsyncSession, task_id: UUID, max_retries: int | None = None) -> bool:
    effective_max = max_retries if max_retries is not None else MAX_RETRIES_DEFAULT
    count = await get_retry_count(db, task_id)
    return count >= effective_max
