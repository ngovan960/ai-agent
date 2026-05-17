"""Audit middleware that logs API requests and broadcasts real-time updates."""

import asyncio
import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        if request.url.path.startswith("/api/"):
            log_entry = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client": request.client.host if request.client else None,
            }
            logger.info(json.dumps(log_entry))

            from services.orchestrator.routers.dashboard import broadcast

            def _handle_broadcast_error(t):
                if not t.cancelled() and t.exception():
                    logger.debug(f"Broadcast failed: {t.exception()}")

            task = asyncio.create_task(broadcast({
                "type": "api_request",
                "data": log_entry,
            }))
            task.add_done_callback(_handle_broadcast_error)

        return response
