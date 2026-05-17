import asyncio
from sqlalchemy import select
from shared.database import async_session_factory
from shared.models.task import Task
from shared.models.registry import AuditLog

async def main():
    async with async_session_factory() as session:
        # Check tasks
        result = await session.execute(select(Task).order_by(Task.created_at.desc()))
        tasks = result.scalars().all()
        print(f"--- TOTAL TASKS: {len(tasks)} ---")
        for t in tasks:
            print(f"Task ID: {t.id} | Title: {t.title} | Status: {t.status} | Created At: {t.created_at}")
            
            # Get audit logs for this task
            audit_result = await session.execute(
                select(AuditLog).where(AuditLog.task_id == t.id).order_by(AuditLog.created_at.asc())
            )
            logs = audit_result.scalars().all()
            print(f"  Audit Logs ({len(logs)}):")
            for log in logs:
                print(f"    [{log.created_at}] Action: {log.action} | Result: {log.result} | Message: {log.message}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
