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
from services.orchestrator.services import dependency_service

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
    total_pages = max(1, (total + page_size - 1) // page_size)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
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


@router.get("/{task_id}/dependencies")
async def list_task_dependencies(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all dependencies of a task with their status."""
    deps = await dependency_service.get_task_dependencies(db, task_id)
    return {"task_id": str(task_id), "dependencies": deps, "total": len(deps)}


@router.post("/{task_id}/dependencies", status_code=201)
async def add_task_dependencies(
    task_id: UUID,
    dependency_ids: list[UUID],
    db: AsyncSession = Depends(get_db),
    dependency_type: str = "blocks",
):
    """Add dependencies to a task with circular dependency check."""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    has_cycle, cycle_path = await dependency_service.has_circular_dependency(
        db, task_id, dependency_ids
    )
    if has_cycle:
        cycle_str = " -> ".join(str(c) for c in (cycle_path or []))
        raise HTTPException(
            status_code=400,
            detail=f"Circular dependency detected: {cycle_str}",
        )

    created = []
    for dep_id in dependency_ids:
        dep = await task_service.add_task_dependency(db, task_id, dep_id, dependency_type)
        if dep:
            created.append(TaskDependencyResponse.model_validate(dep))

    return {"task_id": str(task_id), "added": len(created), "dependencies": created}


@router.get("/{task_id}/dependents")
async def list_task_dependents(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all tasks that depend on this task."""
    deps = await dependency_service.get_dependent_tasks(db, task_id)
    return {"task_id": str(task_id), "dependents": deps, "total": len(deps)}


@router.get("/{task_id}/can-start")
async def check_task_can_start(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Check if a task can start (all its dependencies are DONE)."""
    can, blocked = await dependency_service.can_start(db, task_id)
    return {
        "task_id": str(task_id),
        "can_start": can,
        "blocked_by": [str(b) for b in blocked],
    }
