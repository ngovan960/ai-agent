from datetime import date
from uuid import UUID

from pydantic import BaseModel


class TokenUsage(BaseModel):
    task_id: UUID | None = None
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class MentorCallRecord(BaseModel):
    date: date
    calls_used: int
    calls_limit: int
    can_call: bool


class CostAlert(BaseModel):
    period: str
    total_cost: float
    threshold: float
    exceeded: bool
    message: str


class CostStatsResponse(BaseModel):
    period: str
    total_cost: float
    total_tokens: int
    total_calls: int
    avg_cost_per_call: float
    breakdown_by_model: dict[str, float]


class CostGovernanceResult(BaseModel):
    recommended_model: str
    reason: str
    within_quota: bool
