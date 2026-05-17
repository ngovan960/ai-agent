"""7.6.2 — Prometheus metrics export."""

import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest
    _prometheus_available = True
except ImportError:
    _prometheus_available = False
    logger.info("prometheus_client not installed; metrics disabled")


if _prometheus_available:
    _task_counter = Counter("tasks_total", "Total tasks created", ["status", "project_id"])
    _task_duration = Histogram(
        "task_duration_seconds", "Task execution duration", ["status"],
        buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
    )
    _agent_calls = Counter("agent_calls_total", "Total agent calls", ["agent_name", "status"])
    _retry_counter = Counter("retries_total", "Total retries", ["agent_name", "task_id"])
    _confidence_gauge = Gauge("task_confidence", "Task confidence score", ["task_id"])
    _mentor_quota = Gauge("mentor_quota_remaining", "Mentor quota remaining", ["date"])
    _cost_total = Counter("cost_usd_total", "Total cost in USD", ["model", "agent_name"])
    _active_tasks = Gauge("active_tasks", "Number of active tasks", ["status"])


def export_metrics(name: str, value: float, labels: dict[str, str] | None = None):
    if not _prometheus_available:
        return
    lbls = dict(labels or {})
    try:
        if name == "task.created":
            _task_counter.labels(**lbls).inc(int(value))
        elif name == "task.duration":
            lbls.pop("task_id", None)
            _task_duration.labels(status=lbls.get("status", "unknown")).observe(value)
        elif name == "agent.call":
            _agent_calls.labels(**lbls).inc(int(value))
        elif name == "retry.count":
            _retry_counter.labels(**lbls).inc(int(value))
        elif name == "confidence":
            _confidence_gauge.labels(**lbls).set(value)
        elif name == "mentor.quota":
            _mentor_quota.labels(**lbls).set(value)
        elif name == "cost":
            _cost_total.labels(**lbls).inc(value)
        elif name == "task.active":
            _active_tasks.labels(**lbls).set(value)
    except Exception as e:
        logger.warning("Failed to export metric %s: %s", name, e)


def get_metrics():
    if not _prometheus_available:
        return "# prometheus_client not installed\n"
    return generate_latest(REGISTRY).decode()
