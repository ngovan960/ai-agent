import logging
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.llm.circuit_breaker import CircuitBreaker
from shared.llm.cost_tracker import CostTracker
from shared.llm.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    status: str
    error: str | None = None


class LLMGateway:
    def __init__(
        self,
        db: AsyncSession,
        circuit_breaker: CircuitBreaker | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        from shared.config.settings import get_settings
        from services.execution.opencode_llm_client import OpenCodeLLMClient
        
        self.db = db
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.cost_tracker = CostTracker(db)
        
        settings = get_settings()
        self.opencode_client = OpenCodeLLMClient(
            api_url=settings.OPENCODE_API_URL,
            api_key=settings.OPENCODE_API_KEY,
        )

    async def call(
        self,
        task_id: UUID,
        project_id: UUID | None,
        agent_name: str,
        messages: list[dict[str, str]],
        model_preference: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        timeout: int = 60,
    ) -> LLMResult:
        model = model_preference or "deepseek_v4_flash"
        start = time.time()

        if not self.circuit_breaker.is_model_available(model):
            return LLMResult(
                model=model, content="", input_tokens=0, output_tokens=0,
                cost_usd=0.0, latency_ms=0.0, status="failed",
                error=f"Circuit breaker open for {model}",
            )

        await self.rate_limiter.acquire(model)

        try:
            response = await self.opencode_client.chat_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            if response.error:
                raise Exception(response.error)

            latency = (time.time() - start) * 1000
            self.circuit_breaker.record_success(model)

            result = LLMResult(
                model=model,
                content=response.content,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                latency_ms=latency,
                status="completed",
            )

            await self.cost_tracker.track(
                task_id=task_id,
                agent_name=agent_name,
                model=model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
                latency_ms=int(latency),
                status="completed",
            )

            return result

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.circuit_breaker.record_failure(model)
            logger.error(f"LLM call failed for {model}: {e}")
            return LLMResult(
                model=model, content="", input_tokens=0, output_tokens=0,
                cost_usd=0.0, latency_ms=latency, status="failed", error=str(e),
            )
