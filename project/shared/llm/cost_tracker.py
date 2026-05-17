import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import CostTracking, LLMCallStatus

logger = logging.getLogger(__name__)


class CostTracker:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def track(
        self,
        task_id: UUID,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        status: str = "completed",
        error_message: str | None = None,
    ) -> CostTracking:
        record = CostTracking(
            task_id=task_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=LLMCallStatus.COMPLETED if status == "completed" else LLMCallStatus.FAILED,
            error_message=error_message,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_task_costs(self, task_id: UUID) -> list[CostTracking]:
        result = await self.db.execute(
            select(CostTracking).where(CostTracking.task_id == task_id)
        )
        return result.scalars().all()

    async def get_total_cost(self, task_id: UUID) -> float:
        records = await self.get_task_costs(task_id)
        return sum(r.cost_usd for r in records)
