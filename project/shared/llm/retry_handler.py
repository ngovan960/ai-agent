import asyncio
import logging
import random
import time
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_MULTIPLIER = 2
DEFAULT_INITIAL_DELAY = 1.0

RETRYABLE_ERRORS = {"timeout", "rate_limit", "server_error", "connection_error"}
NON_RETRYABLE_ERRORS = {
    "authentication_failed",
    "invalid_request",
    "context_length_exceeded",
    "invalid_api_key",
}


class RetryExhaustedError(Exception):
    """Raised when all retries have been exhausted."""

    def __init__(self, model: str, attempts: int, last_error: Exception):
        super().__init__(f"All {attempts} retries exhausted for {model}. Last error: {last_error}")
        self.model = model
        self.attempts = attempts
        self.last_error = last_error


class NonRetryableError(Exception):
    """Wraps an error that should not be retried."""

    def __init__(self, error_type: str, original_error: Exception):
        super().__init__(f"Non-retryable error ({error_type}): {original_error}")
        self.error_type = error_type
        self.original_error = original_error


class RetryHandler:
    """Retry LLM calls with exponential backoff and random jitter.

    Usage:
        handler = RetryHandler(max_retries=3, initial_delay=1.0, jitter=True)
        result = await handler.execute(
            lambda: litellm.acompletion(...),
            model="deepseek_v4_flash"
        )
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier
        self.initial_delay = initial_delay
        self.jitter = jitter

    async def execute(
        self,
        call_fn: Callable[[], Awaitable[Any]],
        model: str = "unknown",
        on_retry: Callable[[int, Exception], Awaitable[None]] | None = None,
    ) -> Any:
        """Execute a call with retry logic."""
        last_error: Exception | None = None
        total_attempts = 1 + self.max_retries

        for attempt in range(total_attempts):
            try:
                result = await call_fn()
                if attempt > 0:
                    logger.info(f"Retry successful for {model} on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)

                if error_type in NON_RETRYABLE_ERRORS:
                    logger.warning(f"Non-retryable error for {model}: {error_type} — {e}")
                    raise NonRetryableError(error_type, e)

                if attempt == self.max_retries:
                    logger.error(f"All retries exhausted for {model}: {e}")
                    raise RetryExhaustedError(model, total_attempts, e)

                delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                if self.jitter:
                    delay *= random.uniform(0.5, 1.5)

                logger.warning(
                    f"LLM call failed for {model} (attempt {attempt + 1}/{total_attempts}), "
                    f"retrying in {delay:.2f}s. Error: {error_type} — {e}"
                )

                if on_retry:
                    await on_retry(attempt + 1, e)

                await asyncio.sleep(delay)

        raise RuntimeError("RetryHandler.execute should not reach this point")

    def _classify_error(self, error: Exception) -> str:
        """Classify error to determine if it should be retried."""
        error_str = str(error).lower()
        if hasattr(error, "status_code"):
            status = getattr(error, "status_code")
            if status == 401 or status == 403:
                return "authentication_failed"
            if status == 400:
                return "invalid_request"
            if status == 429:
                return "rate_limit"
            if status in (500, 502, 503, 504):
                return "server_error"
            if status == 408:
                return "timeout"

        if "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        if "rate_limit" in error_str or "rate limit" in error_str or "too many" in error_str:
            return "rate_limit"
        if "context_length" in error_str or "token" in error_str or "exceed" in error_str:
            return "context_length_exceeded"
        if "auth" in error_str or "unauthorized" in error_str or "key" in error_str:
            return "authentication_failed"
        if "connection" in error_str or "refused" in error_str or "eof" in error_str:
            return "connection_error"
        if "server" in error_str or "internal" in error_str:
            return "server_error"

        return "unknown"


def build_retry_on_retry(cb, model: str):
    """Build an on_retry callback that records failures to circuit breaker."""
    async def _on_retry(attempt: int, error: Exception) -> None:
        await cb.record_failure(model)
    return _on_retry
