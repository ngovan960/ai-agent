import asyncio
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls_per_minute = max_calls_per_minute
        self._call_timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, model: str) -> bool:
        async with self._lock:
            now = time.time()
            window_start = now - 60
            timestamps = self._call_timestamps[model]
            timestamps = [t for t in timestamps if t > window_start]
            self._call_timestamps[model] = timestamps

            if len(timestamps) >= self.max_calls_per_minute:
                wait_time = timestamps[0] + 60 - now
                if wait_time > 0:
                    logger.warning(f"Rate limit reached for {model}, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)

            self._call_timestamps[model].append(time.time())
            return True

    async def get_remaining(self, model: str) -> int:
        async with self._lock:
            now = time.time()
            timestamps = [t for t in self._call_timestamps.get(model, []) if t > now - 60]
            return max(0, self.max_calls_per_minute - len(timestamps))

    def reset(self) -> None:
        self._call_timestamps.clear()
