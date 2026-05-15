import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import get_settings
from shared.database import engine, init_db
from shared.cache import close_redis
from services.orchestrator.middleware.audit import AuditMiddleware
from services.orchestrator.routers import projects, modules, tasks, validation

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI SDLC Orchestrator...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down AI SDLC Orchestrator...")
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}
