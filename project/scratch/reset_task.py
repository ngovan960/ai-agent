import asyncio
from sqlalchemy import select, update
from shared.database import async_session_factory
from shared.models.task import Task

async def main():
    async with async_session_factory() as session:
        # Find the latest task
        result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(1))
        task = result.scalar_one_or_none()
        if not task:
            print("No tasks found!")
            return
        
        print(f"Found latest task: {task.id} | Title: {task.title} | Status: {task.status}")
        print("Resetting its status to 'NEW'...")
        
        # Update the task status to NEW
        await session.execute(
            update(Task).where(Task.id == task.id).values(status="NEW")
        )
        await session.commit()
        print("Successfully reset task status to 'NEW'!")

if __name__ == "__main__":
    asyncio.run(main())
