import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.llm.circuit_breaker import CircuitBreaker
from shared.llm.retry_handler import RetryHandler, NonRetryableError, RetryExhaustedError, build_retry_on_retry
from shared.llm.cost_tracker import CostTracker
from shared.llm.rate_limiter import RateLimiter, RateLimitExceededError
from shared.models.registry import LLMCallStatus

logger = logging.getLogger(__name__)

GATEWAY_DEFAULT_TIMEOUT = 60
GATEWAY_DEFAULT_MAX_TOKENS = 4096
GATEWAY_DEFAULT_TEMPERATURE = 0.1


@dataclass
class LLMResult:
    """Result from an LLM call through the gateway."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float
    latency_ms: float
    agent_name: str
    status: str = "completed"
    error: Optional[str] = None


@dataclass
class ModelConfig:
    """Configuration for a model used by the gateway."""
    model: str
    provider: str
    timeout: int = GATEWAY_DEFAULT_TIMEOUT
    max_tokens: int = GATEWAY_DEFAULT_MAX_TOKENS
    temperature: float = GATEWAY_DEFAULT_TEMPERATURE


MODEL_CONFIGS: dict[str, ModelConfig] = {
    "deepseek_v4_flash": ModelConfig(
        model="deepseek/deepseek-chat",
        provider="deepseek",
        timeout=15,
        max_tokens=4096,
    ),
    "deepseek_v4_pro": ModelConfig(
        model="deepseek/deepseek-chat",
        provider="deepseek",
        timeout=60,
        max_tokens=8192,
    ),
    "qwen_3_5_plus": ModelConfig(
        model="qwen/qwen-plus",
        provider="qwen",
        timeout=60,
        max_tokens=8192,
    ),
    "qwen_3_6_plus": ModelConfig(
        model="qwen/qwen-plus-latest",
        provider="qwen",
        timeout=90,
        max_tokens=16384,
    ),
    "minimax_m2_7": ModelConfig(
        model="minimax/abab6.5s-chat",
        provider="minimax",
        timeout=30,
        max_tokens=8192,
    ),
}


DEFAULT_FALLBACKS: dict[str, list[str]] = {
    "deepseek_v4_flash": ["minimax_m2_7", "deepseek_v4_pro"],
    "deepseek_v4_pro": ["qwen_3_6_plus", "minimax_m2_7"],
    "qwen_3_5_plus": ["qwen_3_6_plus", "deepseek_v4_pro"],
    "qwen_3_6_plus": ["deepseek_v4_pro", "minimax_m2_7"],
    "minimax_m2_7": ["deepseek_v4_pro", "qwen_3_5_plus"],
}


class LLMGatewayError(Exception):
    """Base error for LLM Gateway failures."""
    pass


class AllModelsExhaustedError(LLMGatewayError):
    """Raised when all models including fallbacks have failed."""
    def __init__(self, tried_models: list[str]):
        super().__init__(f"All models exhausted: {', '.join(tried_models)}")
        self.tried_models = tried_models


class LLMGateway:
    """Central LLM Gateway — all LLM calls go through this.

    Features:
        - Circuit breaker per model
        - Retry with exponential backoff + jitter
        - Fallback to next model if primary fails
        - Cost + token tracking per call
        - Rate limiting per provider

    Usage:
        gateway = LLMGateway(db_session)
        result = await gateway.call(
            task_id=task_id,
            project_id=project_id,
            agent_name="gatekeeper",
            prompt="...",
            model_preference="deepseek_v4_flash",
        )
    """

    def __init__(
        self,
        db: AsyncSession,
        circuit_breaker: Optional[CircuitBreaker] = None,
        rate_limiter: Optional[RateLimiter] = None,
        retry_handler: Optional[RetryHandler] = None,
    ):
        self.db = db
        self.cost_tracker = CostTracker(db)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(db)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_handler = retry_handler or RetryHandler()

    async def call(
        self,
        task_id: Optional[UUID],
        project_id: Optional[UUID],
        agent_name: str,
        messages: list[dict],
        model_preference: Optional[str] = None,
        max_tokens: int = GATEWAY_DEFAULT_MAX_TOKENS,
        temperature: float = GATEWAY_DEFAULT_TEMPERATURE,
        timeout: int = GATEWAY_DEFAULT_TIMEOUT,
    ) -> LLMResult:
        """Make an LLM call through the gateway with full resilience."""
        tried_models: list[str] = []
        prompt_text = messages[-1]["content"] if messages else ""
        prompt_hash = CostTracker.hash_prompt(prompt_text) if prompt_text else None

        models_to_try = self._build_model_chain(model_preference, agent_name)

        for model_name in models_to_try:
            tried_models.append(model_name)
            model_config = self._get_model_config(model_name)

            if not await self.rate_limiter.check_rate(model_config.provider):
                logger.warning(f"Rate limited for {model_config.provider}, trying next model")
                continue

            if not await self.circuit_breaker.can_call(model_name):
                logger.warning(f"Circuit breaker open for {model_name}, trying next model")
                continue

            try:
                result = await self._execute_call(
                    model_name=model_name,
                    model_config=model_config,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                )

                self.rate_limiter.record_call(model_config.provider)
                await self.circuit_breaker.record_success(model_name)

                result.agent_name = agent_name
                await self.cost_tracker.log_call(
                    task_id=task_id,
                    project_id=project_id,
                    agent_name=agent_name,
                    model=model_name,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=result.latency_ms,
                    status=LLMCallStatus.COMPLETED,
                    prompt_hash=prompt_hash,
                )
                return result

            except NonRetryableError as e:
                logger.warning(f"Non-retryable error for {model_name}: {e}")
                await self.circuit_breaker.record_failure(model_name)
                continue

            except RetryExhaustedError as e:
                logger.warning(f"Retries exhausted for {model_name}: {e}")
                await self.circuit_breaker.record_failure(model_name)
                continue

            except RateLimitExceededError:
                logger.warning(f"Rate limit exhausted for {model_config.provider}")
                continue

            except Exception as e:
                logger.warning(f"Unexpected error for {model_name}: {e}")
                await self.circuit_breaker.record_failure(model_name)
                continue

        raise AllModelsExhaustedError(tried_models)

    async def _execute_call(
        self,
        model_name: str,
        model_config: ModelConfig,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        timeout: int,
    ) -> LLMResult:
        """Execute a single LLM call with retry support."""
        use_timeout = timeout or model_config.timeout
        use_max_tokens = max_tokens or model_config.max_tokens

        on_retry = build_retry_on_retry(self.circuit_breaker, model_name)

        start = time.time()
        try:
            result = await self.retry_handler.execute(
                call_fn=lambda: self._raw_llm_call(
                    model_config.model,
                    messages,
                    temperature,
                    use_max_tokens,
                    use_timeout,
                ),
                model=model_name,
                on_retry=on_retry,
            )
        except NonRetryableError:
            raise
        except RetryExhaustedError:
            raise
        except Exception as e:
            raise

        elapsed = (time.time() - start) * 1000
        content, input_tokens, output_tokens = self._extract_usage(result, model_name)

        cost = self.cost_tracker.estimate_cost(model_name, input_tokens, output_tokens)

        return LLMResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model_name,
            cost_usd=cost,
            latency_ms=elapsed,
            agent_name="",
        )

    async def _raw_llm_call(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> Any:
        """Make the actual LLM API call via LiteLLM."""
        import litellm

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return response

    def _extract_usage(self, response: Any, model_name: str) -> tuple[str, int, int]:
        """Extract content, input_tokens, output_tokens from a LiteLLM response."""
        try:
            content = response.choices[0].message.content or ""
        except (AttributeError, IndexError):
            content = ""

        try:
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
        except (AttributeError, TypeError):
            input_tokens = 0
            output_tokens = 0

        return content, input_tokens, output_tokens

    def _build_model_chain(
        self, model_preference: Optional[str], agent_name: str
    ) -> list[str]:
        """Build the ordered list of models to try."""
        if model_preference:
            chain = [model_preference]
            fallbacks = DEFAULT_FALLBACKS.get(model_preference, [])
            chain.extend(fallbacks)
            return chain

        agent_defaults = {
            "gatekeeper": ["deepseek_v4_flash", "minimax_m2_7", "deepseek_v4_pro"],
            "orchestrator": ["qwen_3_6_plus", "deepseek_v4_pro", "qwen_3_5_plus"],
            "specialist": ["deepseek_v4_pro", "qwen_3_6_plus", "minimax_m2_7"],
            "auditor": ["qwen_3_5_plus", "qwen_3_6_plus", "deepseek_v4_pro"],
            "mentor": ["qwen_3_6_plus", "deepseek_v4_pro", "minimax_m2_7"],
            "devops": ["deepseek_v4_pro", "qwen_3_6_plus", "minimax_m2_7"],
            "monitoring": ["minimax_m2_7", "deepseek_v4_flash", "qwen_3_5_plus"],
        }
        return agent_defaults.get(agent_name, ["deepseek_v4_flash", "deepseek_v4_pro"])

    def _get_model_config(self, model_name: str) -> ModelConfig:
        """Get model configuration."""
        return MODEL_CONFIGS.get(
            model_name,
            ModelConfig(model=model_name, provider="unknown"),
        )
