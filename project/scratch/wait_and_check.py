import asyncio
import time
from sqlalchemy import select
from shared.database import async_session_factory
from shared.models.task import Task
from shared.models.registry import AuditLog

async def main():
    print("Starting progress monitor (polling every 10 seconds)...")
    for i in range(15):
        async with async_session_factory() as session:
            result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(1))
            task = result.scalar_one_or_none()
            if not task:
                print("No tasks found!")
                return
            
            # Get audit logs for this task
            audit_result = await session.execute(
                select(AuditLog).where(AuditLog.task_id == task.id).order_by(AuditLog.created_at.asc())
            )
            logs = audit_result.scalars().all()
            
            print(f"[{time.strftime('%H:%M:%S')}] Task ID: {task.id} | Status: {task.status} | Audit Logs: {len(logs)}")
            if len(logs) > 8:
                print("NEW LOGS DETECTED:")
                for log in logs[8:]:
                    print(f"  [{log.created_at}] Action: {log.action} | Result: {log.result} | Message: {log.message}")
                if task.status in ("ESCALATED", "FAILED", "DONE", "REVIEWING"):
                    print("Task has transitioned to terminal/escalated state. Stopping monitor.")
                    break
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
