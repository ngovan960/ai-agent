from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from shared.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    architecture: str | None = None
    rules: dict = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    tech_stack: list[str] | None = None
    architecture: str | None = None
    rules: dict | None = None


class ProjectResponse(ProjectBase):
    id: UUID
    status: ProjectStatus
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
