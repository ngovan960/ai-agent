import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class RetryHandler:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay

    async def execute(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        retryable_errors: tuple[type[Exception], ...] = (Exception,),
        **kwargs: Any,
    ) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except retryable_errors as e:
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_multiplier ** attempt) + random.uniform(0, 0.5),
                        self.max_delay,
                    )
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
                    raise

    def get_retry_delay(self, attempt: int) -> float:
        return min(
            self.base_delay * (self.backoff_multiplier ** attempt) + random.uniform(0, 0.5),
            self.max_delay,
        )
