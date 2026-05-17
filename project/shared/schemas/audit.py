from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    task_id: UUID | None = None
    action: str
    actor: str
    actor_type: str
    input: dict = {}
    output: dict = {}
    result: str = ""
    message: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
