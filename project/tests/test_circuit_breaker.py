import pytest
from datetime import datetime, timezone
from uuid import uuid4

from shared.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitStateInfo,
    PER_MODEL_CONFIG,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_RECOVERY_TIMEOUT,
    DEFAULT_HALF_OPEN_MAX_CALLS,
)


class TestCircuitBreakerInMemory:
    """Tests for CircuitBreaker without DB persistence (in-memory mode)."""

    @pytest.fixture
    def cb(self):
        return CircuitBreaker()

    def test_initial_state_is_closed(self, cb):
        info = cb._ensure_state("test_model")
        assert info.state == CircuitState.CLOSED
        assert info.failure_count == 0

    async def test_can_call_when_closed(self, cb):
        assert await cb.can_call("test_model") is True

    async def test_opens_after_failures(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        info = cb._ensure_state(model)
        assert info.state == CircuitState.OPEN
        assert info.failure_count == threshold

    async def test_open_blocks_calls(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        assert await cb.can_call(model) is False

    async def test_half_open_transitions_to_closed_on_success(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        info = cb._ensure_state(model)
        info.last_failure_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert await cb.can_call(model) is True
        info = cb._ensure_state(model)
        assert info.state == CircuitState.HALF_OPEN
        await cb.record_success(model)
        info = cb._ensure_state(model)
        assert info.state == CircuitState.CLOSED

    async def test_half_open_transitions_to_open_on_failure(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        info = cb._ensure_state(model)
        info.last_failure_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert await cb.can_call(model) is True
        await cb.record_failure(model)
        info = cb._ensure_state(model)
        assert info.state == CircuitState.OPEN

    async def test_success_resets_failure_count(self, cb):
        model = "test_model"
        for _ in range(3):
            await cb.record_failure(model)
        await cb.record_success(model)
        info = cb._ensure_state(model)
        assert info.failure_count == 0
        assert info.state == CircuitState.CLOSED

    async def test_open_transitions_to_half_open_after_timeout(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        info = cb._ensure_state(model)
        info.last_failure_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert await cb.can_call(model) is True
        info = cb._ensure_state(model)
        assert info.state == CircuitState.HALF_OPEN

    async def test_get_state_info(self, cb):
        model = "test_model"
        await cb.record_failure(model)
        info = await cb.get_state_info(model)
        assert info.model == model
        assert info.failure_count == 1

    async def test_per_model_config_deepseek_flash(self, cb):
        model = "deepseek_v4_flash"
        info = cb._ensure_state(model)
        assert info.recovery_timeout == 30
        assert info.failure_threshold == 5

    async def test_per_model_config_qwen_3_6(self, cb):
        model = "qwen_3_6_plus"
        info = cb._ensure_state(model)
        assert info.recovery_timeout == 90
        assert info.failure_threshold == 3

    async def test_unknown_model_uses_defaults(self, cb):
        model = "unknown_model_v999"
        info = cb._ensure_state(model)
        assert info.recovery_timeout == DEFAULT_RECOVERY_TIMEOUT
        assert info.failure_threshold == DEFAULT_FAILURE_THRESHOLD

    async def test_half_open_limit_calls(self, cb):
        model = "test_model"
        threshold = DEFAULT_FAILURE_THRESHOLD
        for _ in range(threshold):
            await cb.record_failure(model)
        info = cb._ensure_state(model)
        info.last_failure_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        for _ in range(DEFAULT_HALF_OPEN_MAX_CALLS + 1):
            assert await cb.can_call(model) is True
        assert await cb.can_call(model) is False

    async def test_persist_no_db_does_not_crash(self, cb):
        model = "test_model"
        await cb.record_success(model)
        await cb.record_failure(model)
        info = cb._ensure_state(model)
        assert info.failure_count == 1

    async def test_init_from_db_no_db(self, cb):
        await cb.init_from_db(None)
        assert cb.db is None
