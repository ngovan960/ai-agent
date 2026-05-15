"""Authentication middleware for AI SDLC Orchestrator.

Supports:
- JWT Bearer tokens (for human users via dashboard)
- API Key header (for agent/programmatic access)
- Optional: bypass auth in development mode ONLY when explicitly enabled

Security: Auth bypass is only allowed when:
  1. ENVIRONMENT == "development" (explicit opt-in)
  2. AUTH_BYPASS_ENABLED == True (explicit opt-in)
  Both conditions must be true. DEBUG=True alone does NOT bypass auth.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt

from shared.config.settings import get_settings
from shared.security import hash_api_key

logger = logging.getLogger(__name__)

settings = get_settings()

PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/validation/should-skip",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via JWT or API Key."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        if settings.AUTH_BYPASS_ENABLED and settings.ENVIRONMENT == "development":
            logger.warning(
                f"Auth bypass enabled for {request.url.path} "
                f"(ENVIRONMENT={settings.ENVIRONMENT})"
            )
            request.state.user_id = None
            request.state.auth_method = "dev-bypass"
            response = await call_next(request)
            response.headers["X-Auth-Bypass"] = "true"
            return response

        try:
            user_id, auth_method = await self._authenticate(request)
            request.state.user_id = user_id
            request.state.auth_method = auth_method
        except HTTPException as e:
            return self._unauthorized_response(e.detail)

        return await call_next(request)

    async def _authenticate(self, request: Request) -> tuple[Optional[UUID], str]:
        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self._verify_jwt(token), "jwt"

        if api_key:
            return await self._verify_api_key(api_key), "api_key"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header (Bearer token) or X-API-Key header",
        )

    def _verify_jwt(self, token: str) -> Optional[UUID]:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("sub")
            if user_id:
                return UUID(user_id)
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token",
        )

    async def _verify_api_key(self, api_key: str) -> Optional[UUID]:
        try:
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from shared.models.user import ApiKey
            from shared.database import async_session_factory

            hashed = hash_api_key(api_key)

            async with async_session_factory() as db:
                result = await db.execute(
                    select(ApiKey).where(
                        ApiKey.key_hash == hashed,
                        ApiKey.is_active == True,
                    )
                )
                key_record = result.scalars().first()
                if key_record:
                    if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="API key has expired",
                        )
                    key_record.last_used_at = datetime.now(timezone.utc)
                    await db.flush()
                    return key_record.user_id
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"API key verification failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    def _unauthorized_response(self, detail: str):
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail},
        )
