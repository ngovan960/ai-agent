"""Cost Governor — AI SDLC Governance Layer (Phase 5.3)

Tracks token usage, mentor calls, retry loops, and enforces cost limits.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.registry import CostTracking, MentorQuota
from shared.schemas.cost import (
    CostAlert,
    CostGovernanceResult,
    CostStatsResponse,
    MentorCallRecord,
    TokenUsage,
)

logger = logging.getLogger(__name__)

DEFAULT_MENTOR_DAILY_LIMIT = 10
DAILY_COST_THRESHOLD = 50.0
WEEKLY_COST_THRESHOLD = 200.0

MODEL_TIERS = {
    "flash": ["deepseek_v4_flash", "minimax_m2_7"],
    "pro": ["qwen_3_5_plus", "qwen_3_6_plus"],
    "mentor": ["deepseek_v4_pro"],
}


@dataclass
class RetryLoopInfo:
    task_id: UUID
    retry_count: int
    is_loop: bool
    message: str


class CostGovernor:
    """5.3 — Cost Governor for tracking and limiting AI costs."""

    def __init__(self, db_session: AsyncSession | None = None):
        self._db = db_session
        self._mentor_daily_limit = DEFAULT_MENTOR_DAILY_LIMIT

    async def track_tokens(
        self,
        task_id: UUID | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        agent_name: str = "",
        status: str = "completed",
    ) -> TokenUsage:
        """5.3.1 — Track token usage per model call."""
        usage = TokenUsage(
            task_id=task_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

        if self._db:
            record = CostTracking(
                task_id=task_id,
                agent_name=agent_name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status=status,
            )
            self._db.add(record)
            await self._db.flush()

        logger.info(
            f"Token usage: {model} — {usage.total_tokens} tokens "
            f"(in={input_tokens}, out={output_tokens}), cost=${cost_usd:.4f}"
        )
        return usage

    async def track_mentor_call(self, call_date: date | None = None) -> MentorCallRecord:
        """5.3.2 — Track a mentor call and return current quota status."""
        call_date = call_date or date.today()

        if self._db:
            stmt = select(MentorQuota).where(MentorQuota.date == call_date)
            result = await self._db.execute(stmt)
            quota = result.scalar_one_or_none()

            if quota is None:
                quota = MentorQuota(date=call_date, calls_used=0, calls_limit=self._mentor_daily_limit)
                self._db.add(quota)

            quota.calls_used += 1
            await self._db.flush()

            return MentorCallRecord(
                date=quota.date,
                calls_used=quota.calls_used,
                calls_limit=quota.calls_limit,
                can_call=quota.calls_used < quota.calls_limit,
            )
        else:
            return MentorCallRecord(
                date=call_date,
                calls_used=1,
                calls_limit=self._mentor_daily_limit,
                can_call=True,
            )

    async def track_retry_loop(self, task_id: UUID, retry_count: int) -> RetryLoopInfo:
        """5.3.3 — Detect infinite retry loops (>2 retries = loop)."""
        is_loop = retry_count > 2
        return RetryLoopInfo(
            task_id=task_id,
            retry_count=retry_count,
            is_loop=is_loop,
            message=f"Task {task_id} has {retry_count} retries" + (" — possible infinite loop!" if is_loop else ""),
        )

    async def check_mentor_limit(self, call_date: date | None = None) -> bool:
        """5.3.4 — Check if mentor calls are within daily limit."""
        call_date = call_date or date.today()

        if self._db:
            stmt = select(MentorQuota).where(MentorQuota.date == call_date)
            result = await self._db.execute(stmt)
            quota = result.scalar_one_or_none()

            if quota is None:
                return True
            return quota.calls_used < quota.calls_limit

        return True

    async def check_cost_alerts(
        self,
        project_id: UUID | None = None,
        daily_threshold: float = DAILY_COST_THRESHOLD,
        weekly_threshold: float = WEEKLY_COST_THRESHOLD,
    ) -> list[CostAlert]:
        """5.3.5 — Alert when cost exceeds thresholds."""
        alerts = []

        if self._db:
            today = date.today()
            week_ago = today - timedelta(days=7)

            stmt_daily = (
                select(func.sum(CostTracking.cost_usd))
                .where(CostTracking.created_at >= datetime.combine(today, datetime.min.time()))
            )
            if project_id:
                stmt_daily = stmt_daily.where(CostTracking.project_id == project_id)

            result_daily = await self._db.execute(stmt_daily)
            daily_cost = float(result_daily.scalar() or 0.0)

            stmt_weekly = (
                select(func.sum(CostTracking.cost_usd))
                .where(CostTracking.created_at >= datetime.combine(week_ago, datetime.min.time()))
            )
            if project_id:
                stmt_weekly = stmt_weekly.where(CostTracking.project_id == project_id)

            result_weekly = await self._db.execute(stmt_weekly)
            weekly_cost = float(result_weekly.scalar() or 0.0)
        else:
            daily_cost = 0.0
            weekly_cost = 0.0

        if daily_cost > daily_threshold:
            alerts.append(CostAlert(
                period="daily",
                total_cost=round(daily_cost, 2),
                threshold=daily_threshold,
                exceeded=True,
                message=f"Daily cost ${daily_cost:.2f} exceeds threshold ${daily_threshold:.2f}",
            ))

        if weekly_cost > weekly_threshold:
            alerts.append(CostAlert(
                period="weekly",
                total_cost=round(weekly_cost, 2),
                threshold=weekly_threshold,
                exceeded=True,
                message=f"Weekly cost ${weekly_cost:.2f} exceeds threshold ${weekly_threshold:.2f}",
            ))

        return alerts

    async def apply_cost_governance(
        self,
        task_complexity: str = "medium",
        task_budget: float | None = None,
    ) -> CostGovernanceResult:
        """5.3.6 — Recommend model based on task size and quota availability."""
        mentor_within_quota = await self.check_mentor_limit()

        if task_complexity == "low":
            models = MODEL_TIERS["flash"]
            reason = "Low complexity task — using flash model for cost efficiency"
        elif task_complexity == "medium":
            models = MODEL_TIERS["pro"]
            reason = "Medium complexity task — using pro model for balanced performance"
        elif task_complexity == "high":
            if mentor_within_quota:
                models = MODEL_TIERS["mentor"]
                reason = "High complexity task — using mentor model (within quota)"
            else:
                models = MODEL_TIERS["pro"]
                reason = "High complexity task — mentor quota exceeded, falling back to pro"
        else:
            models = MODEL_TIERS["pro"]
            reason = "Unknown complexity — defaulting to pro model"

        return CostGovernanceResult(
            recommended_model=models[0] if models else "unknown",
            reason=reason,
            within_quota=mentor_within_quota,
        )

    async def get_cost_stats(
        self,
        project_id: UUID | None = None,
        period: str = "daily",
    ) -> CostStatsResponse:
        """Get cost statistics for a given period."""
        if self._db:
            now = datetime.now()
            if period == "daily":
                start = now - timedelta(days=1)
            elif period == "weekly":
                start = now - timedelta(weeks=1)
            elif period == "monthly":
                start = now - timedelta(days=30)
            else:
                start = now - timedelta(days=1)

            query = select(
                func.sum(CostTracking.cost_usd).label("total_cost"),
                func.sum(CostTracking.input_tokens + CostTracking.output_tokens).label("total_tokens"),
                func.count(CostTracking.id).label("total_calls"),
            ).where(CostTracking.created_at >= start)

            if project_id:
                query = query.where(CostTracking.project_id == project_id)

            result = await self._db.execute(query)
            row = result.one()

            total_cost = float(row.total_cost or 0.0)
            total_tokens = int(row.total_tokens or 0)
            total_calls = int(row.total_calls or 0)

            breakdown_query = select(
                CostTracking.model,
                func.sum(CostTracking.cost_usd).label("model_cost"),
            ).where(CostTracking.created_at >= start)

            if project_id:
                breakdown_query = breakdown_query.where(CostTracking.project_id == project_id)

            breakdown_query = breakdown_query.group_by(CostTracking.model)
            breakdown_result = await self._db.execute(breakdown_query)
            breakdown = {row.model: float(row.model_cost) for row in breakdown_result}
        else:
            total_cost = 0.0
            total_tokens = 0
            total_calls = 0
            breakdown = {}

        return CostStatsResponse(
            period=period,
            total_cost=round(total_cost, 2),
            total_tokens=total_tokens,
            total_calls=total_calls,
            avg_cost_per_call=round(total_cost / total_calls, 4) if total_calls > 0 else 0.0,
            breakdown_by_model=breakdown,
        )
