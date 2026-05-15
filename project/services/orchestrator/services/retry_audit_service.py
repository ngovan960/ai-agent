from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from shared.models.registry import Retry, AuditLog
from shared.schemas.retry_audit import RetryCreate, AuditLogCreate, AuditLogQuery
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_TASK = 5


class RetryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_retry(self, data: RetryCreate) -> Retry:
        stmt = select(func.count(Retry.id)).where(Retry.task_id == data.task_id)
        result = await self.db.execute(stmt)
        attempt_number = result.scalar() + 1

        if attempt_number > MAX_RETRIES_PER_TASK:
            raise ValueError(f"Max retries ({MAX_RETRIES_PER_TASK}) exceeded for task {data.task_id}")

        retry = Retry(
            task_id=data.task_id,
            attempt_number=attempt_number,
            reason=data.reason.value if hasattr(data.reason, 'value') else str(data.reason),
            agent_name=data.agent_name,
            output=data.output or {},
            error_log=data.error_log,
        )
        self.db.add(retry)
        await self.db.commit()
        await self.db.refresh(retry)
        return retry

    async def get_retries_by_task(self, task_id) -> List[Retry]:
        stmt = select(Retry).where(Retry.task_id == task_id).order_by(Retry.attempt_number)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_retry_stats(self, task_id) -> dict:
        stmt = select(Retry).where(Retry.task_id == task_id).order_by(Retry.attempt_number.desc())
        result = await self.db.execute(stmt)
        retries = list(result.scalars().all())

        if not retries:
            return {
                "task_id": task_id,
                "total_retries": 0,
                "last_retry_reason": None,
                "last_retry_at": None,
                "max_retries_exceeded": False,
            }

        return {
            "task_id": task_id,
            "total_retries": len(retries),
            "last_retry_reason": retries[0].reason,
            "last_retry_at": retries[0].created_at,
            "max_retries_exceeded": len(retries) >= MAX_RETRIES_PER_TASK,
        }

    async def can_retry(self, task_id) -> bool:
        stats = await self.get_retry_stats(task_id)
        return not stats["max_retries_exceeded"]


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_log(self, data: AuditLogCreate) -> AuditLog:
        audit = AuditLog(
            task_id=data.task_id,
            action=data.action,
            actor=data.actor,
            actor_type=data.actor_type,
            input=data.input or {},
            output=data.output or {},
            result=data.result,
            message=data.message,
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit

    async def query_audit_logs(self, query: AuditLogQuery) -> Tuple[List[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count(AuditLog.id))

        if query.task_id:
            stmt = stmt.where(AuditLog.task_id == query.task_id)
            count_stmt = count_stmt.where(AuditLog.task_id == query.task_id)
        if query.actor:
            stmt = stmt.where(AuditLog.actor == query.actor)
            count_stmt = count_stmt.where(AuditLog.actor == query.actor)
        if query.actor_type:
            stmt = stmt.where(AuditLog.actor_type == query.actor_type)
            count_stmt = count_stmt.where(AuditLog.actor_type == query.actor_type)
        if query.result:
            stmt = stmt.where(AuditLog.result == query.result)
            count_stmt = count_stmt.where(AuditLog.result == query.result)
        if query.action:
            stmt = stmt.where(AuditLog.action == query.action)
            count_stmt = count_stmt.where(AuditLog.action == query.action)
        if query.start_date:
            stmt = stmt.where(AuditLog.created_at >= query.start_date)
            count_stmt = count_stmt.where(AuditLog.created_at >= query.start_date)
        if query.end_date:
            stmt = stmt.where(AuditLog.created_at <= query.end_date)
            count_stmt = count_stmt.where(AuditLog.created_at <= query.end_date)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(query.offset).limit(query.limit)
        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())

        return logs, total

    async def get_audit_logs_by_task(self, task_id) -> List[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.task_id == task_id).order_by(AuditLog.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def export_audit_logs_csv(self, query: AuditLogQuery) -> str:
        logs, _ = await self.query_audit_logs(query)
        lines = ["id,task_id,action,actor,actor_type,result,message,created_at"]
        for log in logs:
            lines.append(
                f"{log.id},{log.task_id},{log.action},{log.actor},{log.actor_type},{log.result},"
                f'"{(log.message or "").replace(chr(34), chr(34)+chr(34))}",{log.created_at}'
            )
        return "\n".join(lines)
