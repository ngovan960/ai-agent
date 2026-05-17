import asyncio
from shared.database import async_session_factory
from services.orchestrator.services.workflow_engine import WorkflowEngine
import sys

async def main():
    task_id = sys.argv[1]
    async with async_session_factory() as session:
        engine = WorkflowEngine(session)
        result = await engine.run_workflow(task_id)
        await session.commit()
        print(f"Workflow result: {result}")

asyncio.run(main())
