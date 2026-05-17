import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import AuditLog, AuditResult

logger = logging.getLogger(__name__)


async def get_audit_logs(db: AsyncSession, task_id: UUID | None = None, project_id: UUID | None = None, page: int = 1, page_size: int = 20):
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_q = select(func.count()).select_from(AuditLog)
    if task_id:
        query = query.where(AuditLog.task_id == task_id)
        count_q = count_q.where(AuditLog.task_id == task_id)
    if project_id:
        query = query.where(AuditLog.task.has(project_id=project_id))
        count_q = count_q.where(AuditLog.task.has(project_id=project_id))
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return result.scalars().all(), total


async def create_audit_log(db: AsyncSession, task_id: UUID | None, action: str, actor: str, actor_type: str, input_data: dict | None = None, output_data: dict | None = None, result: str = "SUCCESS", message: str = ""):
    result_enum = AuditResult.SUCCESS if result == "SUCCESS" else AuditResult.FAILURE
    log = AuditLog(
        task_id=task_id, action=action, actor=actor, actor_type=actor_type,
        input=input_data or {}, output=output_data or {},
        result=result_enum, message=message,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log
