from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from shared.models.task import TaskStatus, TaskPriority, RiskLevel


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    owner: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    expected_output: str | None = None
    risk_score: float = Field(default=0.0, ge=0, le=10)
    risk_level: RiskLevel = RiskLevel.LOW


class TaskCreate(TaskBase):
    project_id: UUID
    module_id: UUID | None = None
    max_retries: int = Field(default=2, ge=0, le=5)


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    owner: str | None = None
    priority: TaskPriority | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    expected_output: str | None = None
    risk_score: float | None = Field(None, ge=0, le=10)
    risk_level: RiskLevel | None = None
    cancellation_reason: str | None = None
    failure_reason: str | None = None


class TaskResponse(TaskBase):
    id: UUID
    project_id: UUID
    module_id: UUID | None = None
    status: TaskStatus
    confidence: float
    retries: int
    max_retries: int
    cancellation_reason: str | None = None
    failure_reason: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    cancelled_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskDependencyCreate(BaseModel):
    task_id: UUID
    depends_on_task_id: UUID
    dependency_type: str = Field(default="blocks")


class TaskDependencyResponse(BaseModel):
    id: UUID
    task_id: UUID
    depends_on_task_id: UUID
    dependency_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOutputCreate(BaseModel):
    task_id: UUID
    output_type: str = Field(..., min_length=1, max_length=50)
    content: dict = Field(default_factory=dict)


class TaskOutputResponse(BaseModel):
    id: UUID
    task_id: UUID
    output_type: str
    content: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class StateTransitionRequest(BaseModel):
    target_status: TaskStatus
    reason: str | None = None
