from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StepResult(BaseModel):
    step_name: str
    status: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    errors: list[dict] = []


class VerificationResult(BaseModel):
    task_id: UUID
    mode: str
    status: str
    score: float = 0.0
    steps: list[StepResult] = []
    errors: list[dict] = []
    logs: str = ""
    duration_ms: float = 0.0


class VerificationRequest(BaseModel):
    mode: str = Field(default="dev", pattern="^(dev|prod)$")
    code_path: str | None = None


class VerificationResponse(BaseModel):
    task_id: UUID
    status: str
    score: float
    steps: list[StepResult]
    errors: list[dict]
    duration_ms: float
    mode: str


class VerificationStatusResponse(BaseModel):
    task_id: UUID
    status: str
    score: float
    mode: str
    created_at: datetime | None = None


class RollbackRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class RollbackResponse(BaseModel):
    task_id: UUID
    status: str
    reason: str
    rollback_id: str
    message: str
