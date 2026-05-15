import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import CircuitBreakerState

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_RECOVERY_TIMEOUT = 60
DEFAULT_HALF_OPEN_MAX_CALLS = 3

PER_MODEL_CONFIG = {
    "deepseek_v4_flash": {"failure_threshold": 5, "recovery_timeout": 30},
    "deepseek_v4_pro": {"failure_threshold": 5, "recovery_timeout": 60},
    "qwen_3_5_plus": {"failure_threshold": 5, "recovery_timeout": 60},
    "qwen_3_6_plus": {"failure_threshold": 3, "recovery_timeout": 90},
    "minimax_m2_7": {"failure_threshold": 5, "recovery_timeout": 45},
}


@dataclass
class CircuitStateInfo:
    model: str
    state: CircuitState
    failure_count: int
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    half_open_calls: int = 0
    half_open_at: Optional[datetime] = None
    half_open_max_calls: int = DEFAULT_HALF_OPEN_MAX_CALLS
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    recovery_timeout: int = DEFAULT_RECOVERY_TIMEOUT


class CircuitBreaker:
    """Per-model circuit breaker pattern with DB persistence.

    States:
        CLOSED → normal operation, allow all calls
        OPEN → reject calls after N consecutive failures, use fallback
        HALF_OPEN → allow limited calls to test if recovery succeeded

    Transitions:
        CLOSED → OPEN: after failure_threshold consecutive failures
        OPEN → HALF_OPEN: after recovery_timeout seconds
        HALF_OPEN → CLOSED: one successful call
        HALF_OPEN → OPEN: one failed call (reject immediately)
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._states: dict[str, CircuitStateInfo] = {}
        self._in_memory_fallback: bool = db is None

    async def init_from_db(self, db: AsyncSession) -> None:
        """Load circuit breaker states from database on startup."""
        self.db = db
        try:
            result = await db.execute(select(CircuitBreakerState))
            states = result.scalars().all()
            for cb_state in states:
                model_config = PER_MODEL_CONFIG.get(
                    cb_state.model,
                    {"failure_threshold": DEFAULT_FAILURE_THRESHOLD, "recovery_timeout": DEFAULT_RECOVERY_TIMEOUT},
                )
                self._states[cb_state.model] = CircuitStateInfo(
                    model=cb_state.model,
                    state=CircuitState(cb_state.state),
                    failure_count=cb_state.failure_count or 0,
                    last_failure_at=cb_state.last_failure_at,
                    last_success_at=cb_state.last_success_at,
                    half_open_at=cb_state.half_open_at,
                    failure_threshold=model_config["failure_threshold"],
                    recovery_timeout=model_config["recovery_timeout"],
                )
                logger.debug(f"Loaded circuit breaker state for {cb_state.model}: {cb_state.state}")
            logger.info(f"Initialized {len(states)} circuit breaker states from DB")
        except Exception as e:
            logger.warning(f"Could not load circuit breaker states from DB: {e}")
            self._in_memory_fallback = True

    async def can_call(self, model: str) -> bool:
        """Check if we can make a call to the given model."""
        state = self._ensure_state(model)

        if state.state == CircuitState.CLOSED:
            return True

        if state.state == CircuitState.OPEN:
            elapsed = _seconds_since(state.last_failure_at) if state.last_failure_at else 999
            if elapsed >= state.recovery_timeout:
                await self._transition(model, CircuitState.HALF_OPEN)
                state.half_open_calls = 0
                logger.info(f"Circuit breaker for {model} transitioning OPEN → HALF_OPEN after {elapsed}s")
                return True
            logger.warning(f"Circuit breaker for {model} is OPEN (last failure {elapsed}s ago, timeout {state.recovery_timeout}s)")
            return False

        if state.state == CircuitState.HALF_OPEN:
            if state.half_open_calls < state.half_open_max_calls:
                state.half_open_calls += 1
                return True
            return False

        return False

    async def record_success(self, model: str) -> None:
        """Record a successful call, may transition HALF_OPEN → CLOSED."""
        state = self._ensure_state(model)
        state.last_success_at = datetime.now(timezone.utc)
        state.failure_count = 0

        if state.state == CircuitState.HALF_OPEN:
            await self._transition(model, CircuitState.CLOSED)
            logger.info(f"Circuit breaker for {model} recovered: HALF_OPEN → CLOSED")

        await self._persist(model, state)

    async def record_failure(self, model: str) -> None:
        """Record a failed call, may transition CLOSED → OPEN or HALF_OPEN → OPEN."""
        state = self._ensure_state(model)
        state.failure_count += 1
        state.last_failure_at = datetime.now(timezone.utc)

        if state.state == CircuitState.HALF_OPEN or state.state == CircuitState.CLOSED:
            if state.failure_count >= state.failure_threshold:
                await self._transition(model, CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker for {model} opened after {state.failure_count} failures "
                    f"(threshold: {state.failure_threshold})"
                )

        await self._persist(model, state)

    async def get_state_info(self, model: str) -> CircuitStateInfo:
        """Get current circuit breaker state for a model."""
        return self._ensure_state(model)

    def _ensure_state(self, model: str) -> CircuitStateInfo:
        """Ensure we have state info for the model, initialize if not."""
        if model not in self._states:
            config = PER_MODEL_CONFIG.get(
                model,
                {"failure_threshold": DEFAULT_FAILURE_THRESHOLD, "recovery_timeout": DEFAULT_RECOVERY_TIMEOUT},
            )
            self._states[model] = CircuitStateInfo(
                model=model,
                state=CircuitState.CLOSED,
                failure_count=0,
                failure_threshold=config["failure_threshold"],
                recovery_timeout=config["recovery_timeout"],
            )
        return self._states[model]

    async def _transition(self, model: str, new_state: CircuitState) -> None:
        """Transition circuit breaker to a new state."""
        state = self._ensure_state(model)
        old_state = state.state
        state.state = new_state
        if new_state == CircuitState.HALF_OPEN:
            state.half_open_at = datetime.now(timezone.utc)
            state.half_open_calls = 0
        logger.info(f"Circuit breaker for {model}: {old_state.value} → {new_state.value}")
        await self._persist(model, state)

    async def _persist(self, model: str, state: CircuitStateInfo) -> None:
        """Persist circuit breaker state to database."""
        if self.db is None:
            return
        try:
            result = await self.db.execute(
                select(CircuitBreakerState).where(
                    CircuitBreakerState.model == model
                )
            )
            db_state = result.scalars().first()
            if db_state:
                db_state.state = state.state.value
                db_state.failure_count = state.failure_count
                db_state.last_failure_at = state.last_failure_at
                db_state.last_success_at = state.last_success_at
                db_state.half_open_at = state.half_open_at
                db_state.updated_at = datetime.now(timezone.utc)
            else:
                db_state = CircuitBreakerState(
                    model=model,
                    state=state.state.value,
                    failure_count=state.failure_count,
                    last_failure_at=state.last_failure_at,
                    last_success_at=state.last_success_at,
                    half_open_at=state.half_open_at,
                )
                self.db.add(db_state)
            logger.debug(f"Persisted circuit breaker state for {model}: {state.state.value}")
        except Exception as e:
            logger.warning(f"Could not persist circuit breaker state for {model}: {e}")


def _seconds_since(dt: Optional[datetime]) -> float:
    """Get seconds since a datetime, or a large number if None."""
    if dt is None:
        return 999999
    return (datetime.now(timezone.utc) - dt).total_seconds()
