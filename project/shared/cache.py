import json
import logging
from typing import Any

import redis.asyncio as redis

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10,
        )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def cache_get(key: str) -> Any | None:
    client = await get_redis()
    try:
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Redis cache_get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300):
    client = await get_redis()
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"Redis cache_set error: {e}")


async def cache_delete(key: str):
    client = await get_redis()
    try:
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Redis cache_delete error: {e}")


async def cache_invalidate_pattern(pattern: str):
    client = await get_redis()
    try:
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
    except Exception as e:
        logger.warning(f"Redis cache_invalidate_pattern error: {e}")
