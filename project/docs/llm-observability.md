# LLM Observability

## AI SDLC Orchestrator — Monitoring & Observability

---

## Overview

Phase 7 implements full observability with three pillars:
1. **Tracing**: OpenTelemetry distributed tracing
2. **Metrics**: Prometheus metrics
3. **Logging**: JSON structured logging

---

## 1. Tracing (OpenTelemetry)

**File**: `shared/observability/tracing.py`

### Traced Operations
- Every API request (method, path, status code, duration)
- LLM calls (model, tokens, cost, latency)
- State transitions (from, to, task_id)
- Verification pipeline steps
- Agent dispatch events

### Trace Context
```python
{
    "trace_id": "abc123...",
    "span_id": "def456...",
    "service": "ai-sdlc-orchestrator",
    "operation": "llm_call",
    "attributes": {
        "model": "deepseek-v4-pro",
        "input_tokens": 1500,
        "output_tokens": 800,
        "cost_usd": 0.0039,
        "latency_ms": 2340,
    }
}
```

---

## 2. Metrics (Prometheus)

**File**: `shared/observability/metrics.py`

### Counters
| Metric | Labels | Description |
|--------|--------|-------------|
| `tasks_total` | status | Total tasks by status |
| `tasks_created_total` | — | Total tasks created |
| `tasks_completed_total` | — | Total tasks completed |
| `tasks_failed_total` | — | Total tasks failed |
| `retries_total` | agent | Total retries by agent |
| `llm_calls_total` | model, status | Total LLM calls |
| `cost_usd_total` | model, agent | Total cost in USD |
| `law_violations_total` | severity | Total law violations |
| `mentor_calls_total` | — | Total mentor calls |

### Gauges
| Metric | Labels | Description |
|--------|--------|-------------|
| `active_tasks` | — | Currently active tasks |
| `mentor_quota_remaining` | — | Remaining mentor calls today |
| `task_confidence` | task_id | Task confidence score |
| `circuit_breaker_state` | model | Circuit breaker state (0=closed, 1=open, 2=half-open) |

### Histograms
| Metric | Labels | Description |
|--------|--------|-------------|
| `task_duration_seconds` | status | Task completion time |
| `llm_latency_seconds` | model | LLM call latency |
| `verification_duration_seconds` | step | Verification step duration |
| `api_request_duration_seconds` | method, path | API request latency |

---

## 3. Logging (JSON Structured)

**File**: `shared/observability/logging.py`

### Log Format
```json
{
    "timestamp": "2026-05-17T00:53:30.308Z",
    "level": "INFO",
    "logger": "services.orchestrator.main",
    "message": "Starting AI SDLC Orchestrator...",
    "trace_id": "abc123...",
    "span_id": "def456..."
}
```

### Log Levels
| Level | When |
|-------|------|
| DEBUG | Detailed debugging info |
| INFO | Normal operations |
| WARNING | Potential issues |
| ERROR | Errors that don't crash the system |
| CRITICAL | Fatal errors |

---

## 4. Monitoring Stack

**Directory**: `docker/monitoring/`

### Prometheus
- **Port**: 9090
- **Config**: `prometheus/prometheus.yml`
- **Scrape interval**: 15s
- **Alert rules**: 5 rules in `prometheus/alerts.yml`

### Loki
- **Port**: 3100
- **Config**: `loki/loki-config.yml`
- **Log retention**: 7 days (configurable)

### Promtail
- **Config**: `promtail/promtail-config.yml`
- **Purpose**: Collect logs from `/var/log/sdlc/` and push to Loki

### Grafana
- **Port**: 3000 (or 3001 if dashboard uses 3000)
- **Admin**: admin/admin
- **Auto-provisioned datasources**: Prometheus, Loki
- **Auto-provisioned dashboards**: Task overview, cost tracking, agent performance

---

## 5. Alert Rules

**File**: `docker/monitoring/prometheus/alerts.yml`

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighTaskFailureRate | Failure rate > 10% for 2m | critical |
| MentorQuotaExhausted | Remaining quota < 2 for 1m | warning |
| HighRetryRate | Retry rate > 5/min for 2m | warning |
| LowConfidence | Avg confidence < 40% for 5m | warning |
| CostSpike | Cost rate > $0.10/hour for 5m | info |

---

## 6. Dashboard Metrics

**File**: `services/orchestrator/routers/dashboard.py`

### Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/dashboard/summary` | Projects, tasks, active tasks, instructions, decisions, total cost |
| `GET /api/v1/dashboard/tasks-by-status` | Task counts grouped by status |
| `GET /api/v1/dashboard/cost-breakdown` | Cost breakdown by model |
| `GET /api/v1/dashboard/recent-activity?limit=10` | Recent audit log entries |
| `WS /api/v1/ws` | Real-time WebSocket updates |

### Caching
- In-memory cache with TTL (default 30s)
- Reduces database load for frequently accessed metrics

### Rate Limiting
- Sliding window rate limiting for dashboard API calls
- Prevents abuse of aggregation endpoints

---

## 7. Docker Resource Limits

| Service | Memory Limit | CPU Limit |
|---------|-------------|-----------|
| Prometheus | 512M | 0.5 |
| Loki | 256M | 0.3 |
| Promtail | 128M | 0.2 |
| Grafana | 256M | 0.3 |

---

**Version**: 1.0.0
**Last Updated**: 2026-05-17
**Phase**: 7 (Complete)
