from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    TaskDependencyCreate, TaskDependencyResponse,
    TaskOutputCreate, TaskOutputResponse,
    StateTransitionRequest,
)
from services.orchestrator.services import tasks as task_service

router = APIRouter()


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
    module_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
):
    items, total = await task_service.get_tasks(db, project_id, module_id, page, page_size, status, priority)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = await task_service.create_task(db, data)
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await task_service.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/transition", response_model=TaskResponse)
async def transition_task(
    task_id: UUID, request: StateTransitionRequest, db: AsyncSession = Depends(get_db)
):
    task, error = await task_service.transition_task_state(db, task_id, request)
    if error:
        raise HTTPException(status_code=400 if "not found" not in error.lower() else 404, detail=error)
    return TaskResponse.model_validate(task)


@router.post("/dependencies", response_model=TaskDependencyResponse, status_code=201)
async def add_dependency(data: TaskDependencyCreate, db: AsyncSession = Depends(get_db)):
    dep = await task_service.add_task_dependency(
        db, data.task_id, data.depends_on_task_id, data.dependency_type
    )
    if not dep:
        raise HTTPException(status_code=400, detail="Invalid or duplicate dependency")
    return TaskDependencyResponse.model_validate(dep)


@router.delete("/dependencies/{dep_id}", status_code=204)
async def remove_dependency(dep_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.remove_task_dependency(db, dep_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")


@router.post("/outputs", response_model=TaskOutputResponse, status_code=201)
async def create_output(data: TaskOutputCreate, db: AsyncSession = Depends(get_db)):
    output = await task_service.create_task_output(db, data.task_id, data.output_type, data.content)
    if not output:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOutputResponse.model_validate(output)
