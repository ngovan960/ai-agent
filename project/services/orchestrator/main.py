import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import get_settings
from shared.database import engine, init_db
from shared.cache import close_redis
from services.orchestrator.middleware.audit import AuditMiddleware
from services.orchestrator.middleware.auth import AuthMiddleware
from services.orchestrator.routers import projects, modules, tasks, validation, retry_audit, api_keys

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
] if settings.CORS_ALLOWED_ORIGINS else ["*"]


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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOWED_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)
app.add_middleware(AuditMiddleware)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
app.include_router(retry_audit.router, tags=["retry-audit"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["api-keys"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}
