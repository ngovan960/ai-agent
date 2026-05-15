from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from shared.models.module import ModuleStatus


class ModuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ModuleCreate(ModuleBase):
    project_id: UUID


class ModuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: ModuleStatus | None = None


class ModuleResponse(ModuleBase):
    id: UUID
    project_id: UUID
    status: ModuleStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModuleListResponse(BaseModel):
    items: list[ModuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ModuleDependencyCreate(BaseModel):
    module_id: UUID
    depends_on_module_id: UUID


class ModuleDependencyResponse(BaseModel):
    id: UUID
    module_id: UUID
    depends_on_module_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
