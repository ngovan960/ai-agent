from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://ai_sdlc_user:dev_password@localhost:5432/ai_sdlc"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    LOG_LEVEL: str = "info"
    APP_NAME: str = "AI SDLC Orchestrator"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    OPENCODE_ENABLED: bool = True
    OPENCODE_API_URL: str = "http://localhost:8080"
    OPENCODE_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
