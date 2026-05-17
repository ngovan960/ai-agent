"""Pydantic schemas for MentorInstruction (Phase 6.1)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InstructionCreate(BaseModel):
    task_id: UUID
    instruction_type: str = Field(..., pattern="^(advice|warning|decision|pattern)$")
    content: str
    context: dict[str, Any] = Field(default_factory=dict)


class InstructionUpdate(BaseModel):
    applied: bool | None = None


class InstructionResponse(BaseModel):
    id: UUID
    task_id: UUID | None = None
    instruction_type: str
    content: str
    context: dict[str, Any]
    applied: bool
    embedding: str | None = None
    created_at: datetime
    updated_at: datetime


class InstructionListResponse(BaseModel):
    items: list[InstructionResponse]
    total: int
    page: int
    page_size: int


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=20)
    threshold: float = Field(0.7, ge=0.0, le=1.0)
