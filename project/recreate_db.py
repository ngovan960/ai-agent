import asyncio
from shared.database import engine
from shared.models.base import Base
from shared.models import project, task, registry

async def run():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Recreating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Done!")

asyncio.run(run())
