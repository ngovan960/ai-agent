import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class OptimisticLockError(Exception):
    """Raised when a concurrent update has modified the record since it was read."""

    def __init__(self, message: str = "Record was modified by another process"):
        super().__init__(message)


def retry_on_conflict(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator: retry function on OptimisticLockError with exponential backoff.

    Usage:
        @retry_on_conflict(max_retries=3)
        async def transition_task(task_id, new_status):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except OptimisticLockError as e:
                    last_exception = e
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        f"Optimistic lock conflict on {func.__name__} "
                        f"(attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
