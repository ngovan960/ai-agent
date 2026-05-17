import logging
import time
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class BreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 3


class CircuitBreaker:
    def __init__(self, config: BreakerConfig | None = None):
        self.config = config or BreakerConfig()
        self._states: dict[str, CircuitState] = {}
        self._failure_counts: dict[str, int] = {}
        self._last_failure_times: dict[str, float] = {}
        self._half_open_calls: dict[str, int] = {}

    def get_state(self, model: str) -> CircuitState:
        return self._states.get(model, CircuitState.CLOSED)

    def is_model_available(self, model: str) -> bool:
        state = self.get_state(model)
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            last_fail = self._last_failure_times.get(model, 0)
            if time.time() - last_fail > self.config.recovery_timeout_seconds:
                self._states[model] = CircuitState.HALF_OPEN
                self._half_open_calls[model] = 0
                logger.info(f"Circuit breaker for {model}: OPEN → HALF_OPEN")
                return True
            return False
        if state == CircuitState.HALF_OPEN:
            calls = self._half_open_calls.get(model, 0)
            return calls < self.config.half_open_max_calls
        return True

    def record_success(self, model: str) -> None:
        self._states[model] = CircuitState.CLOSED
        self._failure_counts[model] = 0
        self._half_open_calls[model] = 0
        logger.debug(f"Circuit breaker for {model}: reset to CLOSED")

    def record_failure(self, model: str) -> None:
        self._failure_counts[model] = self._failure_counts.get(model, 0) + 1
        self._last_failure_times[model] = time.time()
        threshold = self.config.failure_threshold
        if self._failure_counts[model] >= threshold:
            self._states[model] = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {model}: CLOSED → OPEN (failure_count={self._failure_counts[model]})")

    def reset(self) -> None:
        self._states.clear()
        self._failure_counts.clear()
        self._last_failure_times.clear()
        self._half_open_calls.clear()
