from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RetryCreate(BaseModel):
    task_id: UUID
    attempt_number: int
    reason: str
    agent_name: str = ""
    error_log: str = ""


class RetryResponse(BaseModel):
    id: UUID
    task_id: UUID
    attempt_number: int
    reason: str
    agent_name: str
    error_log: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RetryListResponse(BaseModel):
    items: list[RetryResponse]
    total: int
    page: int
    page_size: int
