import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
engine = create_async_engine('postgresql+asyncpg://ai_sdlc_user:dev_password@localhost:5432/ai_sdlc')
async def drop_schema():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
asyncio.run(drop_schema())
