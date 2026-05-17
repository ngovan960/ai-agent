import asyncio
from sqlalchemy import select
from shared.database import async_session_factory
from shared.models.task import Task
from shared.models.registry import AuditLog

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(1))
        task = result.scalar_one_or_none()
        if not task:
            print("No tasks found!")
            return
        
        print(f"Latest task: {task.id} | Status: {task.status}")
        
        # Get audit logs for this task
        audit_result = await session.execute(
            select(AuditLog).where(AuditLog.task_id == task.id).order_by(AuditLog.created_at.asc())
        )
        logs = audit_result.scalars().all()
        print(f"Audit Logs ({len(logs)}):")
        for log in logs:
            print(f"  [{log.created_at}] Action: {log.action} | Result: {log.result} | Message: {log.message}")

if __name__ == "__main__":
    asyncio.run(main())
