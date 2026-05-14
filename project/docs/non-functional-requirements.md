# Non-Functional Requirements - AI SDLC System

## Tài liệu Yêu cầu Phiên chức năng

---

## 1. Performance Requirements

### 1.1 API Response Time

| Endpoint Category | Target (p50) | Target (p95) | Target (p99) | Max Timeout |
|---|---|---|---|---|
| Read endpoints (GET) | < 100ms | < 300ms | < 500ms | 3s |
| Write endpoints (POST/PUT/PATCH) | < 200ms | < 500ms | < 1s | 5s |
| State transition (POST /transition) | < 100ms | < 300ms | < 500ms | 3s |
| List endpoints (GET with pagination) | < 200ms | < 500ms | < 1s | 5s |
| Auth endpoints (POST /login, /refresh) | < 50ms | < 100ms | < 200ms | 2s |
| Cost stats aggregation (GET /cost-stats) | < 500ms | < 1s | < 2s | 5s |
| Audit log search (GET /audit-logs) | < 300ms | < 800ms | < 1.5s | 5s |

### 1.2 LLM Call Performance

| Metric | Target | Max | Notes |
|--------|--------|-----|-------|
| Simple classification (Gatekeeper) | < 2s | 15s | DeepSeek V4 Flash |
| Task breakdown (Orchestrator) | < 15s | 90s | Qwen 3.6 Plus |
| Code generation (Specialist) | < 30s | 90s | DeepSeek V4 Pro |
| Code review (Auditor) | < 15s | 60s | DeepSeek V4 Pro |
| Strategic decision (Mentor) | < 30s | 90s | Qwen 3.6 Plus |
| Embedding generation | < 500ms | 5s | text-embedding-3-small |
| Fallback model switch | < 200ms overhead | 1s | Circuit breaker transition |

### 1.3 State Machine Performance

| Operation | Target | Max | Notes |
|-----------|--------|-----|-------|
| Validate transition | < 5ms | 10ms | In-memory validation |
| Execute transition (DB write) | < 50ms | 100ms | Including audit log |
| Read task with state history | < 50ms | 100ms | With up to 20 transitions |
| Concurrent transition (same task) | < 100ms | 200ms | Row-level lock + validation |
| List tasks by state | < 100ms | 300ms | With state index |

### 1.4 Database Performance

| Operation | Target | Max | Notes |
|-----------|--------|-----|-------|
| Single row lookup (by PK) | < 1ms | 5ms | |
| Single row lookup (by index) | < 5ms | 10ms | |
| Paginated query (20 rows) | < 20ms | 50ms | With filters |
| Aggregate query (cost stats) | < 200ms | 500ms | Per project per day |
| Join query (task + transitions) | < 30ms | 50ms | |
| Full-text search | < 100ms | 300ms | ILIKE-based |
| Vector similarity search | < 200ms | 500ms | pgvector, IVFFlat index |

### 1.5 Performance Testing Strategy

```python
# Locust load test configuration
from locust import HttpUser, task, between

class AISDLCLoadTest(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def list_tasks(self):
        self.client.get("/api/v1/tasks", headers=self.headers)

    @task(1)
    def create_task(self):
        self.client.post("/api/v1/tasks", json={...}, headers=self.headers)

    @task(5)
    def get_task_detail(self):
        self.client.get(f"/api/v1/tasks/{self.task_id}", headers=self.headers)

    @task(1)
    def transition_task(self):
        self.client.post(f"/api/v1/tasks/{self.task_id}/transition", json={...})
```

**Load Test Targets:**

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent API requests | 200 req/s | Average load |
| Peak concurrent requests | 500 req/s | Burst capacity |
| Simultaneous task transitions | 50/s | State machine throughput |
| WebSocket connections | 1000 | Dashboard real-time updates |
| LLM concurrent calls | 30 | Across all agents |

---

## 2. Scalability Requirements

### 2.1 Scale Targets

| Metric | Target | Max | Notes |
|--------|--------|-----|-------|
| Concurrent workflows | 100 | 500 | Active task pipelines |
| Total tasks in system | 10,000 | 100,000 | Including completed |
| Active tasks (non-terminal) | 1,000 | 5,000 | Non-terminal states |
| Projects | 100 | 1,000 | |
| Modules per project | 50 | 200 | |
| Tasks per module | 200 | 1,000 | |
| Users | 500 | 5,000 | |
| API keys | 50 | 200 | Per agent type |
| State transitions per task | ~20 avg | 50 max | Including retries |
| Audit log entries | 100,000/day | 500,000/day | |
| LLM call logs | 10,000/day | 50,000/day | |

### 2.2 Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                  (Nginx / HAProxy)                      │
└───────┬──────────────┬──────────────┬───────────────────┘
        │              │              │
   ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
   │ API       │  │ API       │  │ API       │
   │ Server 1  │  │ Server 2  │  │ Server 3  │
   │ (FastAPI)  │  │ (FastAPI)  │  │ (FastAPI)  │
   └────┬──────┘  └────┬──────┘  └────┬──────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
              ┌────────▼────────┐
              │   PostgreSQL      │
              │   (Primary +      │
              │    Read Replicas) │
              └────────┬─────────┘
                       │
              ┌────────▼────────┐
              │   Redis           │
              │   (Cache + Rate   │
              │    Limiting)       │
              └──────────────────┘
```

**Scaling Rules:**

| Component | Scale Trigger | Scaling Method |
|-----------|--------------|----------------|
| API Server | CPU > 70% hoặc request latency > p95 | Horizontal (thêm instances) |
| PostgreSQL | Connection pool > 80% hoặc query latency > target | Read replicas, connection pooling |
| Redis | Memory > 80% | Vertical (tăng memory) hoặc clustering |
| LLM Gateway | Circuit breaker open hoặc queue > 100 | Thêm provider accounts |

### 2.3 Database Scaling

```python
# Connection pooling configuration
DATABASE_CONFIG = {
    "pool_size": 20,           # Connections per API server
    "max_overflow": 10,       # Extra connections when pool exhausted
    "pool_timeout": 30,       # Seconds to wait for connection
    "pool_recycle": 1800,     # Recycle connections after 30 min
    "pool_pre_ping": True,     # Check connection before use
    "echo_pool": False,       # Don't log pool events
}
```

**Read Replicas:**

| Purpose | Configuration | Notes |
|---------|--------------|-------|
| Primary | Read/Write | Single primary cho writes |
| Read Replica 1 | Read-only | Cho GET endpoints, reports |
| Read Replica 2 | Read-only | Cho analytics, cost stats |

**Index Strategy:**

```sql
-- Core indexes (đã có trong schema)
CREATE INDEX idx_tasks_state ON tasks(state);
CREATE INDEX idx_tasks_module_id ON tasks(module_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_state_created_at ON tasks(state, created_at);

-- Composite indexes cho common queries
CREATE INDEX idx_tasks_state_priority ON tasks(state, priority);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_cost_tracking_date ON cost_tracking(date);
CREATE INDEX idx_cost_tracking_project_date ON cost_tracking(project_id, date);
CREATE INDEX idx_llm_call_logs_task ON llm_call_logs(task_id);
CREATE INDEX idx_llm_call_logs_created ON llm_call_logs(created_at);

-- Partial indexes cho filtered queries
CREATE INDEX idx_tasks_active ON tasks(created_at)
    WHERE state NOT IN ('DONE', 'FAILED', 'CANCELLED');

CREATE INDEX idx_tasks_escalated ON tasks(created_at)
    WHERE state = 'ESCALATED';
```

---

## 3. Availability Requirements

### 3.1 Availability Targets

| Component | Target | Max Downtime/Year | Measurement |
|-----------|--------|-------------------|-------------|
| API Server | 99.5% | ~44 hours/year | HTTP 200 response |
| Database | 99.9% | ~8.7 hours/year | Connection success |
| LLM Provider (primary) | 99.0% | ~87 hours/year | Successful response |
| LLM Provider (with fallback) | 99.5% | ~44 hours/year | Any provider success |
| Dashboard | 99.0% | ~87 hours/year | Page load success |

### 3.2 Availability Architecture

```
Client Request
      │
      ▼
┌──────────────┐
│  Health       │
│  Check → 503 │
│  if unhealthy│
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  API Server   │────▶│  Fallback     │
│  (Primary)    │     │  API Server   │
└──────┬───────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  PostgreSQL   │────▶│  PostgreSQL   │
│  (Primary)    │     │  (Replica)    │
└──────────────┘     └──────────────┘
```

### 3.3 Health Check Strategy

```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(),
        "llm_providers": await check_llm_providers(),
    }

    overall = "healthy"
    for component, status in checks.items():
        if status["status"] == "unhealthy":
            overall = "degraded"
        if status["status"] == "error":
            overall = "unhealthy"

    status_code = 200 if overall != "unhealthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "components": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

### 3.4 Graceful Degradation

| Scenario | Degradation | User Impact |
|----------|-------------|-------------|
| Primary DB down | Switch to read replica (read-only) |Không thể tạo/cập nhật tasks, chỉ đọc được |
| Redis down | Skip rate limiting, use in-memory fallback | Rate limiting không hoạt động, có thể bị abuse |
| Primary LLM down | Fallback to secondary provider | Latency tăng, cost có thể tăng |
| All LLM providers down | Queue requests, return 503 | Không thể process tasks mới |
| Single API server down | Load balancer redirect | Không ảnh hưởng user |
| Vector search down | Fall back to LIKE search | Search quality giảm |

---

## 4. Security Requirements

### 4.1 TLS/Encryption

| Layer | Requirement | Standard |
|-------|------------|----------|
| Client → API | TLS 1.2+ | HTTPS mandatory |
| API → Database | TLS 1.2+ | `sslmode=verify-full` |
| API → LLM Provider | TLS 1.2+ | HTTPS mandatory |
| API → Redis | TLS 1.2+ | `rediss://` protocol |
| Agent → API | TLS 1.2+ | API Key over HTTPS |
| Data at rest | AES-256 | pgcrypto for PII columns |

### 4.2 Authentication và Authorization

Chi tiết đầy đủ tại `security-design.md`. Tóm tắt:

| Requirement | Implementation | Reference |
|------------|---------------|-----------|
| JWT authentication | HS256, 15min access, 7day refresh | security-design.md §1 |
| API Key authentication | SHA-256 hash, prefix-based lookup | security-design.md §1.2 |
| RBAC | 4 roles: viewer, developer, operator, admin | security-design.md §2 |
| Per-project permissions | project_members table | security-design.md §2.3 |
| Agent permissions | Permission boundary per agent type | security-design.md §6.4 |
| Rate limiting | Per-role, per-agent rate limits | security-design.md §3.1 |

### 4.3 Secret Management

| Requirement | Implementation |
|------------|---------------|
| Không hardcoded secrets | Env vars only, pre-commit hooks, secret scanners (LAW-005) |
| Secret rotation | JWT 90 ngày, DB password 90 ngày, API keys khi cần |
| Secret storage | Environment variables, không lưu trong DB (trừ hashed passwords/api keys) |
| Backup encryption | `pg_dump` + `gpg` encryption |

### 4.4 Input Validation

| Requirement | Implementation |
|------------|---------------|
| Tất cả input validated | Pydantic models với constraints |
| String length limits | `max_length` trên mọi string field |
| XSS prevention | HTML tag stripping |
| SQL injection prevention | SQLAlchemy ORM (parameterized queries) |
| CSRF protection | Same-site cookies + CSRF token |

---

## 5. Reliability

### 5.1 Circuit Breaker Configuration

Tham chiếu chi tiết tại `llm-integration.md` §2.3.

| Provider | Failure Threshold | Recovery Timeout | Half-Open Max Requests |
|----------|-------------------|-----------------|------------------------|
| DeepSeek | 5 consecutive failures | 30s | 1 |
| Qwen | 5 consecutive failures | 30s | 1 |
| OpenAI (embeddings) | 5 consecutive failures | 30s | 1 |

### 5.2 Retry Policy

| Component | Max Retries | Backoff | Fallback |
|-----------|-------------|---------|----------|
| LLM API calls | 3 | Exponential (1s, 2s, 4s) | Next model in chain |
| Database queries | 3 | Exponential (0.5s, 1s, 2s) | Read replica |
| Redis | 2 | Fixed (1s) | In-memory fallback |
| Task transitions | 2 (state machine max) | N/A | ESCALATED state |

### 5.3 Fallback Strategy

```
LLM Call Fallback Chain:

Primary Model → Retry 3x with backoff → Fallback Model 1 → Retry 3x
→ Fallback Model 2 → Retry 3x → Error Response + Alert

Example (Specialist agent):
DeepSeek V4 Pro → (3 retries) → Qwen 3.6 Plus → (3 retries)
→ Qwen 3.5 Plus → (3 retries) → Error → ESCALATED task
```

### 5.4 Data Integrity

| Requirement | Implementation |
|------------|---------------|
| ACID transactions | PostgreSQL default (READ COMMITTED) |
| State transition atomicity | DB transaction: update task state + insert audit log |
| Audit log immutability | Hash chain (SHA-256), trigger prevent UPDATE/DELETE |
| Concurrent state changes | Row-level locking (SELECT FOR UPDATE) |
| Referential integrity | Foreign keys with ON DELETE CASCADE |
| Backup integrity | pg_dump + gpg encryption, checksum verification |

### 5.5 Error Handling

| Error Type | User Response | Recovery | Logging |
|-----------|--------------|----------|---------|
| Validation error | 400 + error details | Immediate retry by user | Warning level |
| Auth error | 401/403 + error code | Re-authenticate | Info level |
| State transition error | 409 + transition details | Fix state, retry | Warning level |
| LLM timeout | 504 + error message | Fallback model | Error level |
| LLM error | 502 + error message | Fallback model | Error level |
| DB error | 500 + generic message | Retry connection | Error level |
| Internal error | 500 + generic message | Investigate logs | Critical level |

---

## 6. Observability

### 6.1 Logging

| Log Level | Usage | Example |
|-----------|-------|---------|
| CRITICAL | System unavoidable error | Database connection lost |
| ERROR | Operation failure, needs attention | LLM API call failed after retries |
| WARNING | Unexpected but handled situation | Circuit breaker half-open, cost approaching limit |
| INFO | Normal operation event | Task transition, user login, LLM call completed |
| DEBUG | Development detail | Query execution time, context window token count |

**Log Format (Structured JSON):**

```json
{
  "timestamp": "2026-05-14T10:00:00.123Z",
  "level": "INFO",
  "logger": "app.services.state_machine",
  "message": "Task state transition completed",
  "request_id": "req-uuid",
  "trace_id": "trace-uuid",
  "span_id": "span-uuid",
  "context": {
    "task_id": "task-uuid",
    "from_state": "NEW",
    "to_state": "ANALYZING",
    "actor": "gatekeeper",
    "duration_ms": 45
  }
}
```

### 6.2 Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge, Summary

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

# State machine metrics
state_transitions_total = Counter(
    'state_transitions_total',
    'Total state transitions',
    ['from_state', 'to_state']
)

state_transition_duration = Histogram(
    'state_transition_duration_seconds',
    'State transition duration',
    ['from_state', 'to_state'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

active_tasks_by_state = Gauge(
    'active_tasks_by_state',
    'Tasks in non-terminal states',
    ['state']
)

# LLM metrics
llm_call_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['model', 'agent_type', 'status']
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'LLM call duration',
    ['model', 'agent_type'],
    buckets=[0.5, 1, 2.5, 5, 10, 30, 60, 90, 120]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['model', 'token_type']  # token_type: input/output
)

llm_cost_total = Counter(
    'llm_cost_dollars_total',
    'Total LLM cost in dollars',
    ['model', 'agent_type']
)

llm_fallback_total = Counter(
    'llm_fallbacks_total',
    'Total fallback model uses',
    ['primary_model', 'fallback_model']
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['provider', 'model']
)

# Cost metrics
daily_cost_dollars = Gauge(
    'daily_cost_dollars',
    'Daily LLM cost per project',
    ['project_id']
)

# Database metrics
db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)
```

### 6.3 Distributed Tracing

```python
# OpenTelemetry tracing setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanExporter

tracer = trace.get_tracer("ai-sdlc-system")

# Example: Trace state transition
async def transition_task(task_id, from_state, to_state, reason, actor):
    with tracer.start_as_current_span("state_transition") as span:
        span.set_attribute("task.id", task_id)
        span.set_attribute("state.from", from_state)
        span.set_attribute("state.to", to_state)
        span.set_attribute("actor", actor)

        # Inner spans
        with tracer.start_as_current_span("validate_transition"):
            validate(from_state, to_state)

        with tracer.start_as_current_span("persist_transition"):
            result = persist(task_id, from_state, to_state)

        span.set_attribute("transition.id", result.id)
        return result
```

**Trace Context Propagation:**

```
User Request → API Server (trace_id generated)
  → State Machine (span: state_transition)
    → Database (span: db_query)
    → Audit Logger (span: audit_log)
  → LLM Gateway (span: llm_call)
    → Provider API (span: http_request)
    → Cost Tracker (span: cost_tracking)
  → Event Publisher (span: event_publish)
```

---

## 7. Data Retention

### 7.1 Retention Policy

| Data Type | Online Retention | Archive Retention | Archive Storage | Action |
|-----------|-----------------|-------------------|-----------------|--------|
| Active tasks | Indefinite (while project active) | N/A | N/A | Archive when project COMPLETED |
| Completed tasks | 1 year | Additional 2 years | Cold storage (S3 Glacier) | Delete after 3 years |
| Failed/Cancelled tasks | 90 days | Additional 90 days | Cold storage | Delete after 6 months |
| **Audit logs** | **1 year** | **Additional 5 years** | **Cold storage** | **Delete after 6 years** |
| State transitions | Same as task | Same as task | Same as task | Same as task |
| **Cost tracking** | **3 years online** | **Additional 4 years** | **Cold storage** | **Delete after 7 years** |
| LLM call logs | 90 days | N/A | N/A | Delete (keep cost_tracking summary) |
| Users | Indefinite (while active) | N/A | N/A | Anonymize after 1 year inactive |
| API keys | While active + 1 year | N/A | N/A | Delete after revocation + 1 year |
| Revoked tokens | Until expiry | N/A | N/A | Auto-cleanup after expiry |
| Session data | 7 days | N/A | N/A | Delete immediately |
| Prompt template versions | Indefinite | N/A | N/A | Keep all versions for audit |
| Embeddings | Indefinite (while active) | N/A | N/A | Re-embed on model change |

### 7.2 Automated Cleanup Jobs

```python
# app/jobs/cleanup.py
from datetime import date, timedelta
from app.db.session import get_db

async def run_daily_cleanup():
    """Chạy hàng ngày lúc 3AM UTC."""
    db = await anext(get_db())

    # 1. Delete expired revoked tokens
    await db.execute(
        text("DELETE FROM revoked_tokens WHERE expires_at < NOW()")
    )

    # 2. Delete old LLM call logs (giữ cost_tracking summary)
    await db.execute(
        text("DELETE FROM llm_call_logs WHERE created_at < NOW() - INTERVAL '90 days'")
    )

    # 3. Archive old audit logs (1 year → cold storage)
    await db.execute(
        text("""
            INSERT INTO audit_logs_archive
            SELECT * FROM audit_logs
            WHERE created_at < NOW() - INTERVAL '1 year'
        """)
    )
    await db.execute(
        text("DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year'")
    )

    # 4. Delete old failed/cancelled tasks (90 days)
    await db.execute(
        text("""
            DELETE FROM tasks
            WHERE state IN ('FAILED', 'CANCELLED')
            AND updated_at < NOW() - INTERVAL '90 days'
        """)
    )

    # 5. Archive completed tasks (1 year → cold storage)
    await db.execute(
        text("""
            INSERT INTO tasks_archive
            SELECT * FROM tasks
            WHERE state = 'DONE'
            AND updated_at < NOW() - INTERVAL '1 year'
        """)
    )
    await db.execute(
        text("""
            DELETE FROM tasks
            WHERE state = 'DONE'
            AND updated_at < NOW() - INTERVAL '1 year'
        """)
    )

    # 6. Purge old session data (7 days)
    await db.execute(
        text("DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '7 days'")
    )

    # 7. Anonymize inactive users (1 year)
    await db.execute(
        text("""
            UPDATE users SET
                email = CONCAT('anonymized_', id, '@deleted.com'),
                full_name = 'Anonymized User',
                is_active = FALSE
            WHERE last_login < NOW() - INTERVAL '1 year'
            AND is_active = TRUE
        """)
    )

    await db.commit()
```

---

## 8. Backup and Recovery Strategy

### 8.1 Backup Schedule

| Backup Type | Frequency | Retention | Method | Storage |
|------------|-----------|-----------|--------|---------|
| Full database | Daily (3AM UTC) | 30 days | `pg_dump` + `gpg` | S3 (encrypted) |
| WAL archiving | Continuous | 7 days | PostgreSQL WAL | S3 (encrypted) |
| Configuration | On change | Indefinite | Git repository | GitHub (private) |
| LLM prompt templates | On change | Indefinite | DB versioned + Git | Both |
| Audit logs archive | Monthly | 6 years | Cold storage | S3 Glacier |

### 8.2 Backup Encryption

```bash
#!/bin/bash
# scripts/backup_database.sh
# Chạy hàng ngày lúc 3AM UTC qua cron

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="ai_sdlc_db"
S3_BUCKET="s3://ai-sdlc-backups"
GPG_RECIPIENT="ai-sdlc-backup@example.com"

# Full database backup
pg_dump \
  --format=custom \
  --compress=9 \
  --dbname="$DATABASE_URL" \
  > "/tmp/${DB_NAME}_${TIMESTAMP}.dump"

# Encrypt với GPG
gpg --encrypt \
  --recipient "$GPG_RECIPIENT" \
  --output "/tmp/${DB_NAME}_${TIMESTAMP}.dump.gpg" \
  "/tmp/${DB_NAME}_${TIMESTAMP}.dump"

# Upload to S3
aws s3 cp \
  "/tmp/${DB_NAME}_${TIMESTAMP}.dump.gpg" \
  "${S3_BUCKET}/daily/${TIMESTAMP}.dump.gpg" \
  --storage-class STANDARD_IA

# Verify upload
aws s3 ls "${S3_BUCKET}/daily/${TIMESTAMP}.dump.gpg"

# Cleanup local files
rm -f "/tmp/${DB_NAME}_${TIMESTAMP}.dump"
rm -f "/tmp/${DB_NAME}_${TIMESTAMP}.dump.gpg"

# Delete backups older than retention period
aws s3 ls "${S3_BUCKET}/daily/" | \
  awk '{print $4}' | \
  while read -r key; do
    file_date=$(echo "$key" | cut -d'_' -f1 | cut -d'/' -f2)
    if [ "$file_date" < "$(date -d '30 days ago' +%Y%m%d)" ]; then
      aws s3 rm "${S3_BUCKET}/daily/${key}"
    fi
  done

echo "Backup completed: ${TIMESTAMP}"
```

### 8.3 Recovery Procedures

| Scenario | RTO | RPO | Recovery Procedure |
|----------|-----|-----|-------------------|
| Single row corruption | < 1 hour | 0 | Point-in-time recovery using WAL |
| Table corruption | < 2 hours | < 5 min | Restore from latest backup + WAL replay |
| Full database loss | < 4 hours | < 1 hour | Restore full backup + WAL replay |
| Configuration loss | < 30 min | 0 | Clone from Git repository |
| Region failure | < 8 hours | < 4 hours | Failover to DR region |

### 8.4 Disaster Recovery

```
Recovery Priority:
1. Database restoration (highest priority)
2. API services
3. Agent runtime
4. Dashboard/UI (lowest priority)

DR Architecture:
- Primary Region: us-east-1
- DR Region: us-west-2 (warm standby)
- RPO: 1 hour (WAL archiving interval)
- RTO: 4 hours (full restoration time)
- Failover: Manual (require human approval)
```

### 8.5 Backup Testing

```
Monthly Backup Recovery Test:

1. Tạo test database từ latest backup
2. Verify tất cả tables và indexes tồn tại
3. Verify data integrity (row counts, constraints)
4. Verify application có thể connect và hoạt động
5. Measure recovery time
6. Document results
7. Alert if recovery time exceeds RTO
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*