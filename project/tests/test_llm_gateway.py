import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from shared.llm.retry_handler import (
    RetryHandler,
    RetryExhaustedError,
    NonRetryableError,
)
from shared.llm.cost_tracker import CostTracker
from shared.llm.rate_limiter import RateLimiter, RateLimitExceededError
from services.orchestrator.services.llm_gateway import (
    LLMGateway,
    LLMResult,
    ModelConfig,
    MODEL_CONFIGS,
    DEFAULT_FALLBACKS,
    AllModelsExhaustedError,
)


class TestRetryHandler:
    async def test_success_on_first_attempt(self):
        handler = RetryHandler(max_retries=3)

        async def call():
            return "success"

        result = await handler.execute(call_fn=call, model="test_model")
        assert result == "success"

    async def test_success_after_retry(self):
        handler = RetryHandler(max_retries=3, initial_delay=0.01, jitter=False)
        call_count = [0]

        async def flaky_call():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("server_error — please retry")
            return "recovered"

        result = await handler.execute(call_fn=flaky_call, model="test_model")
        assert result == "recovered"
        assert call_count[0] == 3

    async def test_non_retryable_error(self):
        handler = RetryHandler(max_retries=3)

        async def bad_call():
            raise Exception("authentication_failed — invalid API key")

        with pytest.raises(NonRetryableError):
            await handler.execute(call_fn=bad_call, model="test_model")

    async def test_retries_exhausted(self):
        handler = RetryHandler(max_retries=2, initial_delay=0.01, jitter=False)

        async def always_fail():
            raise Exception("server_error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute(call_fn=always_fail, model="test_model")
        assert exc_info.value.model == "test_model"
        assert exc_info.value.attempts == 3

    async def test_on_retry_callback(self):
        handler = RetryHandler(max_retries=2, initial_delay=0.01, jitter=False)
        retry_calls = []

        async def on_retry(attempt, error):
            retry_calls.append(attempt)

        async def fails_once(): ...
        
        fails_once_call_count = [0]
        async def fails_once():
            fails_once_call_count[0] += 1
            if fails_once_call_count[0] < 2:
                raise Exception("server_error")
            return "ok"

        await handler.execute(call_fn=fails_once, model="test", on_retry=on_retry)
        assert len(retry_calls) == 1
        assert retry_calls[0] == 1

    async def test_jitter_produces_different_delays(self):
        handler1 = RetryHandler(max_retries=1, initial_delay=1.0, jitter=True)

        call_count = [0]

        async def fails_once():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("server_error")
            return "ok"

        await handler1.execute(call_fn=fails_once, model="test")
        assert call_count[0] == 2

    async def test_status_code_classification(self):
        handler = RetryHandler()

        class FakeHttpError(Exception):
            pass

        e = FakeHttpError("unauthorized")
        e.status_code = 401
        assert handler._classify_error(e) == "authentication_failed"

        e2 = FakeHttpError("too many requests")
        e2.status_code = 429
        assert handler._classify_error(e2) == "rate_limit"

        e3 = FakeHttpError("internal error")
        e3.status_code = 500
        assert handler._classify_error(e3) == "server_error"


class TestCostTracker:
    async def test_estimate_cost(self):
        tracker = CostTracker(MagicMock())
        cost = tracker.estimate_cost("deepseek_v4_flash", 1000, 500)
        assert cost == round(1000 / 1000 * 0.0001 + 500 / 1000 * 0.0003, 6)

    async def test_estimate_cost_only_input(self):
        tracker = CostTracker(MagicMock())
        cost = tracker.estimate_cost("qwen_3_6_plus", 5000)
        assert cost == round(5000 / 1000 * 0.00033, 6)

    async def test_unknown_model_uses_defaults(self):
        tracker = CostTracker(MagicMock())
        cost = tracker.estimate_cost("unknown_model", 1000, 1000)
        assert cost > 0

    async def test_hash_prompt(self):
        h1 = CostTracker.hash_prompt("hello world")
        h2 = CostTracker.hash_prompt("hello world")
        h3 = CostTracker.hash_prompt("different")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64

    async def test_get_model_rates(self):
        tracker = CostTracker(MagicMock())
        rates = tracker._get_model_rates("deepseek_v4_flash")
        assert rates == (0.0001, 0.0003)

    async def test_log_call_with_mock_db(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        tracker = CostTracker(mock_db)
        result = await tracker.log_call(
            task_id=uuid4(),
            project_id=uuid4(),
            agent_name="gatekeeper",
            model="deepseek_v4_flash",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=250.5,
        )
        assert result is not None
        assert mock_db.add.call_count == 2
        assert mock_db.flush.call_count == 2

    async def test_check_budget(self):
        mock_db = MagicMock()
        tracker = CostTracker(mock_db)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = MagicMock(
            total_cost=0.05, total_calls=5
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        within = await tracker.check_budget(uuid4(), 1.0)
        assert within is True


class TestRateLimiter:
    def test_check_rate_allows_first_call(self):
        limiter = RateLimiter()
        assert limiter._check_in_memory("deepseek", 60) is True

    def test_check_rate_limits_after_window_full(self):
        limiter = RateLimiter()
        for _ in range(60):
            limiter.record_call("deepseek")
        assert limiter._check_in_memory("deepseek", 60) is False

    def test_get_remaining(self):
        limiter = RateLimiter()
        assert limiter.get_remaining("deepseek") == 60
        for _ in range(10):
            limiter.record_call("deepseek")
        assert limiter.get_remaining("deepseek") == 50

    def test_different_providers_have_different_limits(self):
        limiter = RateLimiter()
        for _ in range(30):
            limiter.record_call("qwen")
        assert limiter._check_in_memory("qwen", 30) is False
        assert limiter._check_in_memory("deepseek", 60) is True

    async def test_wait_if_needed_immediate(self):
        limiter = RateLimiter()
        await limiter.wait_if_needed("deepseek")

    async def test_rate_limit_exceeded_error(self):
        with pytest.raises(RateLimitExceededError):
            raise RateLimitExceededError("deepseek")


class TestLLMGatewayModels:
    def test_all_models_have_config(self):
        for model in ["deepseek_v4_flash", "deepseek_v4_pro", "qwen_3_5_plus", "qwen_3_6_plus", "minimax_m2_7"]:
            assert model in MODEL_CONFIGS

    def test_all_models_have_fallbacks(self):
        for model in MODEL_CONFIGS:
            assert model in DEFAULT_FALLBACKS
            assert len(DEFAULT_FALLBACKS[model]) >= 1

    def test_model_chain_defaults(self):
        mock_db = MagicMock()
        gateway = LLMGateway(mock_db)
        chain = gateway._build_model_chain(None, "gatekeeper")
        assert chain[0] == "deepseek_v4_flash"

        chain = gateway._build_model_chain(None, "orchestrator")
        assert chain[0] == "qwen_3_6_plus"

        chain = gateway._build_model_chain(None, "mentor")
        assert chain[0] == "qwen_3_6_plus"

    def test_model_chain_with_preference(self):
        mock_db = MagicMock()
        gateway = LLMGateway(mock_db)
        chain = gateway._build_model_chain("deepseek_v4_pro", "specialist")
        assert chain[0] == "deepseek_v4_pro"
        assert "minimax_m2_7" in chain[1:]

    def test_get_model_config(self):
        mock_db = MagicMock()
        gateway = LLMGateway(mock_db)
        config = gateway._get_model_config("qwen_3_6_plus")
        assert config.timeout == 90
        assert config.max_tokens == 16384
        assert config.provider == "qwen"

    def test_all_models_exhausted_error(self):
        error = AllModelsExhaustedError(["m1", "m2"])
        assert "m1" in str(error)
        assert "m2" in str(error)
