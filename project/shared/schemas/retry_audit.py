from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class RetryReason(str, Enum):
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMITED = "llm_rate_limited"
    LLM_ERROR = "llm_error"
    VALIDATION_FAILED = "validation_failed"
    EXECUTION_ERROR = "execution_error"
    STATE_CONFLICT = "state_conflict"


class RetryCreate(BaseModel):
    task_id: UUID
    reason: RetryReason
    agent_name: str
    error_log: Optional[str] = None
    output: Optional[dict] = None


class RetryResponse(BaseModel):
    id: UUID
    task_id: UUID
    attempt_number: int
    reason: str
    agent_name: str
    output: Optional[dict]
    error_log: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RetryStats(BaseModel):
    task_id: UUID
    total_retries: int
    last_retry_reason: Optional[str]
    last_retry_at: Optional[datetime]
    max_retries_exceeded: bool


class AuditLogCreate(BaseModel):
    task_id: Optional[UUID] = None
    action: str
    actor: str
    actor_type: str = "agent"
    input: Optional[dict] = None
    output: Optional[dict] = None
    result: str
    message: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: UUID
    task_id: Optional[UUID]
    action: str
    actor: str
    actor_type: str
    input: Optional[dict]
    output: Optional[dict]
    result: str
    message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogQuery(BaseModel):
    task_id: Optional[UUID] = None
    actor: Optional[str] = None
    actor_type: Optional[str] = None
    result: Optional[str] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
