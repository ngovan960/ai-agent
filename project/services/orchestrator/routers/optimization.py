from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services.multi_project_service import MultiProjectService
from services.orchestrator.services.workflow_optimizer_service import WorkflowOptimizerService
from shared.database import get_db

router = APIRouter()


@router.get("/multi-project/status", tags=["optimization"])
async def get_multi_project_status(db: AsyncSession = Depends(get_db)):
    service = MultiProjectService(db)
    projects = await service.get_all_projects_status(db)
    allocation = await service.allocate_resources(projects)
    return {
        "projects": projects,
        "allocation": allocation["allocation"],
    }


@router.get("/multi-project/dependencies", tags=["optimization"])
async def get_cross_project_dependencies(db: AsyncSession = Depends(get_db)):
    service = MultiProjectService(db)
    deps = await service.check_cross_project_dependencies(db)
    return {"dependencies": deps}


@router.get("/optimization/performance", tags=["optimization"])
async def get_workflow_performance(db: AsyncSession = Depends(get_db)):
    optimizer = WorkflowOptimizerService(db)
    return await optimizer.analyze_workflow_performance(db)


@router.get("/optimization/suggestions", tags=["optimization"])
async def get_optimization_suggestions(db: AsyncSession = Depends(get_db)):
    optimizer = WorkflowOptimizerService(db)
    suggestions = await optimizer.suggest_optimizations(db)
    return {"suggestions": suggestions}
