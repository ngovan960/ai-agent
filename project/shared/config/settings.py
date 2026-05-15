from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DATABASE_URL: str = "postgresql+asyncpg://ai_sdlc_user:dev_password@localhost:5432/ai_sdlc"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    LOG_LEVEL: str = "info"
    APP_NAME: str = "AI SDLC Orchestrator"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ALLOWED_ORIGINS: str = ""
    AUTH_BYPASS_ENABLED: bool = False
    JWT_ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
