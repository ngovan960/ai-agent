from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services import modules as module_service
from services.orchestrator.services import tasks as task_service
from shared.database import get_db
from shared.schemas.module import (
    ModuleCreate,
    ModuleDependencyCreate,
    ModuleDependencyResponse,
    ModuleListResponse,
    ModuleResponse,
    ModuleUpdate,
)
from shared.schemas.task import TaskListResponse, TaskResponse

router = APIRouter()


@router.get("/", response_model=ModuleListResponse)
async def list_modules(
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    items, total = await module_service.get_modules(db, project_id, page, page_size, status)
    return ModuleListResponse(
        items=[ModuleResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(module_id: UUID, db: AsyncSession = Depends(get_db)):
    module = await module_service.get_module(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return ModuleResponse.model_validate(module)


@router.get("/{module_id}/tasks", response_model=TaskListResponse)
async def list_module_tasks(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
):
    items, total = await task_service.get_tasks(db, module_id=module_id, page=page, page_size=page_size, status=status, priority=priority)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=ModuleResponse, status_code=201)
async def create_module(data: ModuleCreate, db: AsyncSession = Depends(get_db)):
    module = await module_service.create_module(db, data)
    return ModuleResponse.model_validate(module)


@router.put("/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: UUID, data: ModuleUpdate, db: AsyncSession = Depends(get_db)
):
    module = await module_service.update_module(db, module_id, data)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return ModuleResponse.model_validate(module)


@router.delete("/{module_id}", status_code=204)
async def delete_module(module_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await module_service.delete_module(db, module_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Module not found")


@router.post("/dependencies", response_model=ModuleDependencyResponse, status_code=201)
async def add_dependency(data: ModuleDependencyCreate, db: AsyncSession = Depends(get_db)):
    dep = await module_service.add_module_dependency(db, data.module_id, data.depends_on_module_id)
    if not dep:
        raise HTTPException(status_code=400, detail="Invalid or duplicate dependency")
    return ModuleDependencyResponse.model_validate(dep)


@router.delete("/dependencies/{dep_id}", status_code=204)
async def remove_dependency(dep_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await module_service.remove_module_dependency(db, dep_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")
