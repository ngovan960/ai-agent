"""7.6.3 — Structured JSON logging."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_entry["span_id"] = record.span_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "ctx"):
            log_entry["context"] = record.ctx
        return json.dumps(log_entry, default=str)


def setup_json_logging(level: str = "INFO"):
    logger = logging.getLogger()
    if any(hasattr(h, "formatter") and isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def log_event(level: str, message: str, context: dict | None = None, trace_id: str | None = None):
    logger = logging.getLogger(__name__)
    extra = {}
    if context:
        extra["ctx"] = context
    if trace_id:
        extra["trace_id"] = trace_id
    logger.log(getattr(logging, level.upper(), logging.INFO), message, extra=extra)
