import hashlib
import logging
from uuid import UUID as UUIDType

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import CostTracking, LLMCallLog, LLMCallStatus

logger = logging.getLogger(__name__)

DEFAULT_COST_PER_1K_INPUT = 0.0001
DEFAULT_COST_PER_1K_OUTPUT = 0.0003


class CostTracker:
    """Track LLM call costs and token usage per task/project."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._model_costs: dict[str, tuple[float, float]] = self._load_default_costs()

    def _load_default_costs(self) -> dict[str, tuple[float, float]]:
        """Load default cost rates per model (per 1K tokens)."""
        return {
            "deepseek_v4_flash": (0.0001, 0.0003),
            "deepseek_v4_pro": (0.00043, 0.00087),
            "qwen_3_5_plus": (0.00039, 0.00234),
            "qwen_3_6_plus": (0.00033, 0.00195),
            "minimax_m2_7": (0.00026, 0.00120),
        }

    def _get_model_rates(self, model: str) -> tuple[float, float]:
        """Get input/output cost rates for a model."""
        model_lower = model.lower().replace("/", "_").replace("-", "_").replace(" ", "_")
        for key, rates in self._model_costs.items():
            if key in model_lower or model_lower in key:
                return rates
        return (DEFAULT_COST_PER_1K_INPUT, DEFAULT_COST_PER_1K_OUTPUT)

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int | None = None,
    ) -> float:
        """Estimate USD cost for given token counts."""
        input_rate, output_rate = self._get_model_rates(model)
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = 0.0
        if output_tokens:
            output_cost = (output_tokens / 1000) * output_rate
        return round(input_cost + output_cost, 6)

    async def log_call(
        self,
        task_id: UUIDType | None,
        project_id: UUIDType | None,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        status: LLMCallStatus = LLMCallStatus.COMPLETED,
        error_message: str | None = None,
        retry_count: int = 0,
        circuit_breaker_triggered: bool = False,
        prompt_hash: str | None = None,
    ) -> CostTracking:
        """Log an LLM call to cost tracking tables."""
        cost_tracking = CostTracking(
            task_id=task_id,
            project_id=project_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.estimate_cost(model, input_tokens, output_tokens),
            latency_ms=int(latency_ms),
            status=status,
            error_message=error_message,
        )
        self.db.add(cost_tracking)
        await self.db.flush()

        call_log = LLMCallLog(
            task_id=task_id,
            cost_tracking_id=cost_tracking.id,
            agent_name=agent_name,
            model=model,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=int(latency_ms),
            status=status,
            error_message=error_message,
            retry_count=retry_count,
            circuit_breaker_triggered=circuit_breaker_triggered,
        )
        self.db.add(call_log)
        await self.db.flush()

        logger.debug(
            f"Logged LLM call: agent={agent_name} model={model} "
            f"tokens={input_tokens}/{output_tokens} cost=${cost_tracking.cost_usd:.6f}"
        )
        return cost_tracking

    async def get_task_cost(self, task_id: UUIDType) -> dict:
        """Get total cost for a task."""
        result = await self.db.execute(
            select(
                func.sum(CostTracking.input_tokens).label("total_input"),
                func.sum(CostTracking.output_tokens).label("total_output"),
                func.sum(CostTracking.cost_usd).label("total_cost"),
                func.count(CostTracking.id).label("total_calls"),
                func.avg(CostTracking.latency_ms).label("avg_latency"),
            ).where(CostTracking.task_id == task_id)
        )
        row = result.one_or_none()
        if row:
            return {
                "task_id": task_id,
                "total_input_tokens": row.total_input or 0,
                "total_output_tokens": row.total_output or 0,
                "total_cost_usd": round(row.total_cost or 0, 6),
                "total_calls": row.total_calls or 0,
                "avg_latency_ms": round(row.avg_latency or 0, 2),
            }
        return {
            "task_id": task_id,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "avg_latency_ms": 0.0,
        }

    async def get_project_cost(self, project_id: UUIDType) -> dict:
        """Get total cost for a project."""
        result = await self.db.execute(
            select(
                func.sum(CostTracking.cost_usd).label("total_cost"),
                func.count(CostTracking.id).label("total_calls"),
            ).where(CostTracking.project_id == project_id)
        )
        row = result.one_or_none()
        return {
            "project_id": project_id,
            "total_cost_usd": round(row.total_cost or 0, 6),
            "total_calls": row.total_calls or 0,
        }

    async def check_budget(self, task_id: UUIDType, budget_usd: float) -> bool:
        """Check if task's cost is within budget."""
        task_cost = await self.get_task_cost(task_id)
        return task_cost["total_cost_usd"] <= budget_usd

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        """Create a SHA-256 hash of the prompt for deduplication."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:64]
