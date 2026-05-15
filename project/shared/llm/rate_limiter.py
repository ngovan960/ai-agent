import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

RATE_LIMITS = {
    "deepseek": 60,
    "qwen": 30,
    "minimax": 30,
    "default": 30,
}
WINDOW_SECONDS = 60


class RateLimiter:
    """Rate limiter with Redis support and in-memory fallback.

    Uses a sliding window per provider:
    - Redis mode: atomic INCR + EXPIRE
    - In-memory mode: timestamps list per provider
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._in_memory_requests: dict[str, list[float]] = defaultdict(list)

    async def check_rate(self, provider: str) -> bool:
        """Check if a request can be made for the given provider.
        
        Returns True if the request is allowed, False if rate limited.
        """
        limit = RATE_LIMITS.get(provider.lower(), RATE_LIMITS["default"])

        if self.redis:
            return await self._check_redis(provider, limit)
        return self._check_in_memory(provider, limit)

    async def wait_if_needed(self, provider: str) -> None:
        """Wait until the rate limit allows another request."""
        import asyncio

        max_wait = 30
        waited = 0
        while not await self.check_rate(provider):
            if waited >= max_wait:
                raise RateLimitExceededError(
                    provider, "Rate limit still exceeded after max wait"
                )
            await asyncio.sleep(1)
            waited += 1

    def record_call(self, provider: str) -> None:
        """Record a call for rate limiting purposes."""
        if not self.redis:
            self._in_memory_requests[provider.lower()].append(time.time())
            self._cleanup_in_memory(provider.lower())

    async def _check_redis(self, provider: str, limit: int) -> bool:
        """Check rate limit using Redis."""
        try:
            key = f"rate_limit:{provider.lower()}"
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, WINDOW_SECONDS)
            return current <= limit
        except Exception as e:
            logger.warning(f"Redis rate limit check failed, falling back to in-memory: {e}")
            return self._check_in_memory(provider, limit)

    def _check_in_memory(self, provider: str, limit: int) -> bool:
        """Check rate limit using in-memory timestamps list."""
        self._cleanup_in_memory(provider)
        count = len(self._in_memory_requests[provider.lower()])
        return count < limit

    def _cleanup_in_memory(self, provider: str) -> None:
        """Remove timestamps older than the sliding window."""
        now = time.time()
        cutoff = now - WINDOW_SECONDS
        self._in_memory_requests[provider] = [
            ts for ts in self._in_memory_requests[provider]
            if ts > cutoff
        ]

    def get_remaining(self, provider: str) -> int:
        """Get remaining requests allowed for the current window."""
        limit = RATE_LIMITS.get(provider.lower(), RATE_LIMITS["default"])
        if provider.lower() not in self._in_memory_requests:
            return limit
        self._cleanup_in_memory(provider)
        used = len(self._in_memory_requests[provider.lower()])
        return max(0, limit - used)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, provider: str, message: str = "Rate limit exceeded"):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
