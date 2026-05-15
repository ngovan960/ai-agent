import time
import json
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4()),
        )
        request.state.correlation_id = correlation_id

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        if not request.url.path.startswith("/api/"):
            return response

        client_ip = self._get_client_ip(request)
        user_id = str(getattr(request.state, "user_id", None)) if hasattr(request.state, "user_id") else None
        auth_method = getattr(request.state, "auth_method", None)

        log_entry = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_string": str(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
            "user_id": user_id,
            "auth_method": auth_method,
        }

        logger.info(json.dumps(log_entry))
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else None
