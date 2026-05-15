from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas.module import (
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleListResponse,
    ModuleDependencyCreate, ModuleDependencyResponse,
)
from services.orchestrator.services import modules as module_service

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
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ModuleListResponse(
        items=[ModuleResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(module_id: UUID, db: AsyncSession = Depends(get_db)):
    module = await module_service.get_module(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return ModuleResponse.model_validate(module)


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


@router.get("/{module_id}/tasks")
async def list_module_tasks(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
):
    from shared.schemas.task import TaskListResponse, TaskResponse
    from services.orchestrator.services import tasks as task_service
    items, total = await task_service.get_tasks(db, None, module_id, page, page_size, status, priority)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
