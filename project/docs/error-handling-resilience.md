# Error Handling & Resilience

## AI SDLC Orchestrator — Resilience Mechanisms

---

## 1. Circuit Breaker

**File**: `shared/llm/circuit_breaker.py`

Each LLM model has its own circuit breaker with 3 states:

```
CLOSED ──5 failures──▶ OPEN ──60s timeout──▶ HALF_OPEN ──3 successes──▶ CLOSED
  │                      │                       │
  │                      │                       └─ 1 failure ──▶ OPEN
  │                      │
  └─ Normal operation    └─ All calls fail immediately
```

### Configuration
| Parameter | Value |
|-----------|-------|
| Failure threshold | 5 consecutive failures |
| Recovery timeout | 60 seconds |
| Half-open max calls | 3 |

### State Persistence
Circuit breaker state is stored in `circuit_breaker_state` table:
- `model`: Model identifier
- `state`: CLOSED, OPEN, or HALF_OPEN
- `failure_count`: Current failure count
- `last_failure_at`: Timestamp of last failure
- `last_success_at`: Timestamp of last success
- `half_open_at`: When circuit transitioned to HALF_OPEN

---

## 2. Retry with Exponential Backoff

**File**: `shared/llm/retry_handler.py`

### LLM API Retries
| Parameter | Value |
|-----------|-------|
| Max retries | 3 |
| Base delay | 1.0 second |
| Backoff multiplier | 2.0x |
| Max delay | 60.0 seconds |
| Jitter | Random 0-0.5s added |

### Delay Formula
```
delay = min(base_delay × multiplier^attempt + random(0, 0.5), max_delay)
```

### Retryable Errors
- `timeout` — Request timed out
- `rate_limit` — Rate limit exceeded (429)
- `server_error` — 5xx errors

### Non-Retryable Errors
- `auth_failed` — Invalid API key
- `invalid_request` — Malformed request
- `context_length_exceeded` — Prompt too long

---

## 3. Task-Level Retry

**File**: `services/orchestrator/services/retry_service.py`

| Parameter | Value |
|-----------|-------|
| Max retries per task | 2 |
| After max retries | Escalate to Mentor |

Retries are tracked in the `retries` table with attempt number, reason, and agent name.

---

## 4. Fallback Model Chain

When a model's circuit breaker is OPEN, the router tries fallback models:

```
deepseek-v4-flash → deepseek-v4-pro → qwen-3.6-plus
qwen-3.5-plus     → qwen-3.6-plus
qwen-3.6-plus     → No fallback → Escalate to human
```

---

## 5. Workflow Engine Resilience

**File**: `services/orchestrator/services/workflow_engine.py`

### Per-State Retries
- Each workflow state can retry up to 2 times
- After max retries → transition to ESCALATED
- Mentor takes over from ESCALATED state

### Timeout Protection
- Workflow timeout: 1800 seconds (30 minutes)
- Per-node timeout: Configurable per verification step
- Timeout → transition to BLOCKED or ESCALATED

### Optimistic Locking
- State transitions use optimistic locking
- Concurrent transition conflicts are caught and retried
- `OptimisticLockError` → retry with fresh state

---

## 6. Rollback Engine

**File**: `services/orchestrator/services/rollback_service.py`

### Auto-Rollback Triggers
- Verification score < 60
- Confidence score < 0.30
- Critical law violation detected

### Rollback Methods
| Method | Description | Timeout |
|--------|-------------|---------|
| Git revert | Revert last commit | 30s |
| Snapshot restore | pg_restore from backup | 60s |

### Configuration
- `auto_rollback`: true (default)
- `manual_approval`: false (default)
- `max_rollbacks`: 3
- `revert_method`: git_revert

---

## 7. Graceful Degradation

### Redis Fallback
If Redis is unavailable, the cache falls back to in-memory dict:

```python
# shared/cache.py
try:
    redis_client.get(key)
except ConnectionError:
    in_memory_cache.get(key)  # Fallback
```

### Database Fallback
If PostgreSQL is unavailable:
- API returns 503 Service Unavailable
- Health check fails
- Docker healthcheck restarts container

---

## 8. Error Classification

### HTTP Error Responses
| Code | When |
|------|------|
| 400 | Invalid request body |
| 401 | Missing/invalid auth |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Optimistic lock conflict |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable (DB down) |

### Task Error States
| State | Cause | Recovery |
|-------|-------|----------|
| BLOCKED | Dependency not met | Resolve dependency |
| ESCALATED | Max retries exceeded | Mentor takeover |
| FAILED | Mentor rejected / fatal error | Manual intervention |
| CANCELLED | User requested cancel | None (terminal) |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
