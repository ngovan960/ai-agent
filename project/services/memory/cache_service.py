"""Cache Service — Phase 6.5: Redis cache with TTL and hit rate tracking."""

import asyncio
import logging
from typing import Any

from shared.cache import cache_delete as _cache_delete
from shared.cache import cache_get as _cache_get
from shared.cache import cache_invalidate_pattern as _cache_invalidate
from shared.cache import cache_set as _cache_set

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600
CACHE_STATS_KEY = "cache:stats"

TTL_CONFIG = {
    "task": 300,
    "memory_search": 600,
    "law_check": 1800,
    "embedding": 86400,
    "instruction": 3600,
    "decision": 3600,
}

_hit_count: int = 0
_miss_count: int = 0
_stats_lock: asyncio.Lock = asyncio.Lock()


async def _incr_hit():
    global _hit_count
    async with _stats_lock:
        _hit_count += 1


async def _incr_miss():
    global _miss_count
    async with _stats_lock:
        _miss_count += 1


async def cache_get(key: str) -> Any | None:
    """6.5.1 — Get value from cache."""
    value = await _cache_get(key)
    if value is not None:
        await _incr_hit()
    else:
        await _incr_miss()
    return value


async def cache_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """6.5.1 — Set value in cache with TTL."""
    try:
        await _cache_set(key, value, ttl=ttl or DEFAULT_TTL)
        return True
    except Exception as e:
        logger.warning(f"cache_set failed for {key}: {e}")
        return False


async def cache_invalidate(key: str) -> bool:
    """6.5.3 — Invalidate a specific cache key."""
    try:
        await _cache_delete(key)
        return True
    except Exception as e:
        logger.warning(f"cache_invalidate failed for {key}: {e}")
        return False


async def cache_invalidate_pattern(pattern: str) -> bool:
    """6.5.3 — Invalidate all keys matching a pattern."""
    try:
        await _cache_invalidate(pattern)
        return True
    except Exception as e:
        logger.warning(f"cache_invalidate_pattern failed for {pattern}: {e}")
        return False


def get_ttl(cache_type: str) -> int:
    """6.5.4 — Get TTL for a cache type."""
    return TTL_CONFIG.get(cache_type, DEFAULT_TTL)


def get_cache_stats() -> dict:
    """6.5.5 — Get cache hit rate statistics."""
    total = _hit_count + _miss_count
    return {
        "hits": _hit_count,
        "misses": _miss_count,
        "total": total,
        "hit_rate": round(_hit_count / total, 4) if total > 0 else 0.0,
    }


def reset_cache_stats():
    """Reset cache statistics."""
    global _hit_count, _miss_count
    _hit_count = 0
    _miss_count = 0
