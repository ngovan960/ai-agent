from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidenceBreakdown(BaseModel):
    test_pass_rate: float = Field(ge=0, le=1, description="T component")
    lint_score: float = Field(ge=0, le=1, description="L component")
    retry_penalty: float = Field(ge=0, le=1, description="P component")
    law_compliance: float = Field(ge=0, le=1, description="A component")


class ConfidenceResponse(BaseModel):
    task_id: UUID
    confidence_score: float = Field(ge=0, le=1)
    breakdown: ConfidenceBreakdown
    action: str
    calculated_at: datetime


class ConfidenceHistoryEntry(BaseModel):
    task_id: UUID
    confidence_score: float
    breakdown: ConfidenceBreakdown
    action: str
    calculated_at: datetime


class ConfidenceHistoryResponse(BaseModel):
    task_id: UUID
    history: list[ConfidenceHistoryEntry]
    total_entries: int
