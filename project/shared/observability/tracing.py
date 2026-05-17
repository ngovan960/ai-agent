"""7.6.1 — OpenTelemetry tracing instrumentation."""

import logging
import os
from contextlib import contextmanager
from uuid import UUID

logger = logging.getLogger(__name__)

_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
_tracer = None

if _enabled:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)
        logger.info("OpenTelemetry tracing enabled, exporting to %s", endpoint)
    except Exception as e:
        logger.warning("Failed to init OpenTelemetry: %s", e)


def get_tracer(name: str | None = None):
    if _tracer:
        from opentelemetry import trace
        return trace.get_tracer(name or __name__)
    return None


@contextmanager
def instrument_agent(agent_name: str, task_id: UUID | None = None, attributes: dict | None = None):
    if not _tracer:
        yield
        return
    from opentelemetry.trace import Status, StatusCode
    attrs = {"agent.name": agent_name}
    if task_id:
        attrs["task.id"] = str(task_id)
    if attributes:
        attrs.update(attributes)
    with _tracer.start_as_current_span(f"agent.{agent_name}", attributes=attrs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


async def create_trace(context: dict | None = None) -> str | None:
    if not _tracer:
        return None
    span = _tracer.start_span("workflow.trace")
    trace_id = format(span.get_span_context().trace_id, "032x")
    if context:
        span.set_attribute("workflow.context", str(context))
    span.end()
    return trace_id

