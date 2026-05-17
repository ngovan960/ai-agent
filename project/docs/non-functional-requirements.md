# Non-Functional Requirements

## AI SDLC Orchestrator — NFRs

---

## 1. Performance

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| API response time (p95) | < 2 seconds | Prometheus histogram |
| API response time (p99) | < 5 seconds | Prometheus histogram |
| LLM call latency (p95) | < 10 seconds | Cost tracker |
| Verification pipeline | < 10 minutes total | Verification service |
| Database query time (p95) | < 100ms | SQLAlchemy logging |
| Dashboard page load | < 3 seconds | Next.js metrics |
| WebSocket message delivery | < 500ms | WebSocket latency |

---

## 2. Scalability

| Requirement | Target |
|-------------|--------|
| Concurrent tasks | 100+ |
| API requests/second | 1000+ |
| Database connections | 50+ (connection pool) |
| LLM calls/minute | 60+ (rate limited) |
| Dashboard concurrent users | 50+ |

---

## 3. Reliability

| Requirement | Target |
|-------------|--------|
| Uptime | ≥ 99% |
| Data loss | Zero (PostgreSQL WAL) |
| Task completion rate | ≥ 80% |
| Verification pass rate | ≥ 80% first attempt |
| Mean time to recovery (MTTR) | < 5 minutes |

---

## 4. Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | JWT + API Key |
| Authorization | Role-based (admin, developer, viewer) |
| Data encryption | TLS in transit, encrypted at rest |
| Secret management | Environment variables, no hardcoded secrets |
| Audit trail | All API requests logged |
| Input validation | Pydantic schemas |
| SQL injection prevention | SQLAlchemy ORM (parameterized queries) |
| XSS prevention | React auto-escaping |
| CSRF protection | SameSite cookies |

---

## 5. Maintainability

| Requirement | Implementation |
|-------------|----------------|
| Code coverage | ≥ 70% (pytest) |
| Type safety | Python type hints, TypeScript |
| Linting | ruff (Python), eslint (TypeScript) |
| Documentation | 16 design docs, inline comments |
| Logging | JSON structured logging |
| Monitoring | Prometheus + Grafana |
| Testing | 478 unit tests |

---

## 6. Cost Efficiency

| Requirement | Target |
|-------------|--------|
| Average task cost | < $0.05 |
| Daily mentor cost | < $1.00 (10 calls max) |
| Monthly infrastructure | < $100 (self-hosted) |
| LLM cost tracking | Per-call logging |
| Cost alerts | Prometheus alert at $0.10/hour |

---

## 7. Observability

| Requirement | Implementation |
|-------------|----------------|
| Tracing | OpenTelemetry |
| Metrics | Prometheus (counters, gauges, histograms) |
| Logging | JSON structured, centralized (Loki) |
| Dashboards | Grafana (auto-provisioned) |
| Alerts | 5 Prometheus alert rules |
| Health checks | Docker healthcheck for all services |

---

## 8. Compliance

| Requirement | Implementation |
|-------------|----------------|
| Architectural laws | 20 laws enforced by Law Engine |
| Audit trail | All state changes logged |
| Data retention | Configurable (default 90 days) |
| Mentor quota | 10 calls/day, database-enforced |
| Confidence scoring | TLPA formula, clamped [0, 1] |
| Terminal state immutability | DONE/FAILED/CANCELLED cannot be changed |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
