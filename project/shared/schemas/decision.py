"""Pydantic schemas for Decision (Phase 6.3)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    project_id: UUID
    task_id: UUID | None = None
    decision: str
    reason: str
    context: dict[str, Any] = Field(default_factory=dict)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    id: UUID
    project_id: UUID
    task_id: UUID | None = None
    decision: str
    reason: str
    context: dict[str, Any]
    alternatives: list[dict[str, Any]]
    decided_by: str
    created_at: datetime
    updated_at: datetime


class DecisionListResponse(BaseModel):
    items: list[DecisionResponse]
    total: int
    page: int
    page_size: int
