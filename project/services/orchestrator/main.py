import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from services.memory.router import router as memory_router
from services.orchestrator.middleware.audit import AuditMiddleware
from services.orchestrator.routers import (
    agents,
    audit_logs,
    deployments,
    governance,
    modules,
    optimization,
    projects,
    tasks,
)
from services.orchestrator.routers.dashboard import router as dashboard_router
from services.orchestrator.routers.deployments import init_deployment
from services.orchestrator.services.approval_service import ApprovalService
from services.orchestrator.services.deployment_service import DeploymentService
from services.orchestrator.services.rollback_service import RollbackEngine
from shared.cache import close_redis, get_redis
from shared.config.settings import get_settings
from shared.database import async_session_factory, engine, get_db, init_db
from shared.models.task import Task, TaskStatus
from shared.observability.logging import setup_json_logging

settings = get_settings()

setup_json_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

_workflow_worker_task = None
_shutdown_requested = False


async def _workflow_background_worker():
    """Background worker that picks up pending tasks with row-level locking.

    Uses SELECT FOR UPDATE SKIP LOCKED to prevent duplicate processing
    when multiple workers are running (or same worker on fast poll cycles).
    """
    global _shutdown_requested
    while not _shutdown_requested:
        try:
            async with async_session_factory() as session:
                from services.orchestrator.services.workflow_engine import WorkflowEngine
                from sqlalchemy.orm import selectinload

                # Use FOR UPDATE SKIP LOCKED to prevent concurrent processing
                # of the same task across overlapping poll cycles
                result = await session.execute(
                    select(Task).options(
                        selectinload(Task.dependencies),
                        selectinload(Task.outputs),
                        selectinload(Task.retry_records)
                    ).where(
                        Task.status.in_([
                            TaskStatus.NEW,
                            TaskStatus.ESCALATED,
                            TaskStatus.BLOCKED,
                        ])
                    ).with_for_update(skip_locked=True)
                    .limit(1)
                )
                task = result.scalars().first()
                if task:
                    try:
                        wf_engine = WorkflowEngine(session)
                        await wf_engine.run_workflow(task.id)
                        await session.commit()
                        logger.info(f"Workflow completed for task {task.id}")
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Workflow failed for task {task.id}: {e}")
        except Exception as e:
            logger.error(f"Workflow worker error: {e}", exc_info=True)
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _workflow_worker_task
    logger.info("Starting AI SDLC Orchestrator...")
    await init_db()
    logger.info("Database initialized")
    ds = DeploymentService(None, None, None)
    approval_svc = ApprovalService()
    rollback_eng = RollbackEngine()
    init_deployment(ds, approval_svc, rollback_eng)
    logger.info("Deployment, approval, and rollback services initialized")

    _workflow_worker_task = asyncio.create_task(_workflow_background_worker())
    logger.info("Workflow background worker started")

    yield
    logger.info("Shutting down AI SDLC Orchestrator...")
    global _shutdown_requested
    _shutdown_requested = True
    if _workflow_worker_task:
        # Give the worker up to 30s to finish current task before force-cancelling
        logger.info("Draining workflow worker (30s timeout)...")
        try:
            await asyncio.wait_for(asyncio.shield(_workflow_worker_task), timeout=30)
        except (TimeoutError, asyncio.CancelledError):
            _workflow_worker_task.cancel()
            logger.warning("Workflow worker force-cancelled after drain timeout")
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(audit_logs.router, prefix="/api/v1", tags=["audit"])
app.include_router(governance.router, prefix="/api/v1", tags=["governance"])
app.include_router(memory_router, prefix="/api/v1", tags=["memory"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(deployments.router, prefix="/api/v1", tags=["deploy"])
app.include_router(optimization.router, prefix="/api/v1", tags=["optimization"])


@app.get("/health")
async def health_check():
    db_status = "unknown"
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            db_status = "healthy"
            break
    except Exception:
        db_status = "unhealthy"

    redis_status = "unknown"
    try:
        r = await get_redis()
        await r.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": db_status,
            "redis": redis_status,
        },
    }


@app.get("/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    db_ok = redis_ok = False
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            db_ok = True
            break
    except Exception:
        pass
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass
    return {
        "ready": db_ok and redis_ok,
        "checks": {"database": db_ok, "redis": redis_ok},
    }
