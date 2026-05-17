"""Tests for Observability (Phase 7.6)."""

import json
import logging
from unittest.mock import patch

from shared.observability.logging import JSONFormatter, log_event, setup_json_logging
from shared.observability.metrics import export_metrics, get_metrics
from shared.observability.tracing import create_trace, get_tracer, instrument_agent


class TestJSONFormatter:
    def test_format_basic(self):
        logger = logging.getLogger("test_json")
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        record = logger.makeRecord("test_json", logging.INFO, "test.py", 10, "hello world", (), None)
        formatted = JSONFormatter().format(record)
        parsed = json.loads(formatted)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["logger"] == "test_json"
        assert "timestamp" in parsed

    def test_format_with_trace_id(self):
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        record.trace_id = "abc123"
        formatted = JSONFormatter().format(record)
        parsed = json.loads(formatted)
        assert parsed["trace_id"] == "abc123"

    def test_format_with_context(self):
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        record.ctx = {"key": "val"}
        formatted = JSONFormatter().format(record)
        parsed = json.loads(formatted)
        assert parsed["context"]["key"] == "val"


class TestSetupJsonLogging:
    def test_setup_does_not_duplicate(self):
        setup_json_logging("INFO")
        json_handlers = [h for h in logging.getLogger().handlers
                         if hasattr(h, "formatter") and isinstance(h.formatter, JSONFormatter)]
        setup_json_logging("INFO")
        json_handlers2 = [h for h in logging.getLogger().handlers
                          if hasattr(h, "formatter") and isinstance(h.formatter, JSONFormatter)]
        assert len(json_handlers2) == len(json_handlers)
        assert len(json_handlers) == len(json_handlers2) > 0


class TestLogEvent:
    def test_log_event_with_context(self, caplog):
        caplog.set_level(logging.INFO)
        logging.getLogger("shared.observability.logging")
        log_event("INFO", "test event", context={"file": "test.py"})
        assert "test event" in caplog.text


class TestMetrics:
    def test_export_metrics_without_prometheus(self):
        export_metrics("task.created", 1, {"status": "DONE", "project_id": "p1"})
        get_metrics()

    def test_get_metrics_without_prometheus(self):
        result = get_metrics()
        assert "prometheus_client not installed" in result

    def test_export_does_not_mutate_labels(self):
        labels = {"status": "DONE", "project_id": "p1"}
        original = dict(labels)
        export_metrics("task.created", 1, labels)
        assert labels == original


class TestTracing:
    def test_get_tracer_disabled(self):
        with patch.dict("os.environ", {"OTEL_ENABLED": "false"}):
            # Re-run module-level code
            import os

            import shared.observability.tracing as t
            t._enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
            t._tracer = None
            assert get_tracer() is None

    def test_instrument_agent_disabled(self):
        with patch.dict("os.environ", {"OTEL_ENABLED": "false"}):
            import shared.observability.tracing as t
            t._enabled = False
            t._tracer = None
            with instrument_agent("test_agent") as span:
                assert span is None

    async def test_create_trace_disabled(self):
        import shared.observability.tracing as t
        t._enabled = False
        t._tracer = None
        result = await create_trace({"key": "val"})
        assert result is None
