import asyncio
from sqlalchemy import text
from shared.database import engine, async_session_factory
from shared.models.task import Task, TaskStatus, TaskPriority, RiskLevel
from shared.models.project import Project, ProjectStatus

async def main():
    # Fix enum
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE TYPE project_status AS ENUM ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED');"))
        except Exception:
            pass
            
    async with async_session_factory() as session:
        project = Project(name="Web Profile Test", description="Testing OpenCode CLI", status=ProjectStatus.ACTIVE)
        session.add(project)
        await session.flush()
        
        task = Task(
            title="Tạo trang web profile đơn giản",
            description="Create index.html with a simple user profile UI.",
            project_id=project.id,
            status=TaskStatus.IMPLEMENTING,  # Go straight to Specialist
            priority=TaskPriority.MEDIUM,
            risk_level=RiskLevel.LOW,
            expected_output="index.html"
        )
        session.add(task)
        await session.commit()
        print(f"Created Task ID: {task.id} in IMPLEMENTING status")

asyncio.run(main())
