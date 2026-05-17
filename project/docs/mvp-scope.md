# MVP Scope

## AI SDLC Orchestrator — Minimum Viable Product

---

## Definition

The MVP proves the core workflow works end-to-end: a user describes a task, and the system autonomously analyzes, plans, implements, verifies, and completes it.

---

## Included Phases (0-7)

### Phase 0: System Design ✅
- 20 architectural laws
- 11-state state machine with 22 valid transitions
- Database schema (20 tables)
- 16 design documents
- 10 agent prompt templates

### Phase 1: Core State System ✅
- CRUD APIs for Projects, Modules, Tasks
- SQLAlchemy ORM models (20 tables)
- Alembic migrations
- Redis cache with in-memory fallback
- Pydantic request/response schemas

### Phase 2: Workflow Engine ✅
- State machine execution
- Node-to-agent mapping
- Per-state retry mechanism (max 2)
- Workflow timeout (30 min)
- Optimistic locking for concurrent transitions
- Audit logging for every transition

### Phase 3: Agent Runtime ✅
- 10 agent prompt templates
- LLM Gateway (OpenCode + OpenCode)
- Dynamic Model Router
- Circuit breaker per model
- Retry handler with exponential backoff
- Cost tracking per LLM call

### Phase 4: Verification Sandbox ✅
- 5-step pipeline: lint → unit test → integration test → build → security
- Dev mode (OpenCode tools) and Prod mode (Docker sandbox)
- Mode selection based on risk level
- Fail-fast for critical steps
- Score threshold (60/100)

### Phase 5: Governance Layer ✅
- Confidence Engine (TLPA formula)
- Law Engine (20 laws, regex-based detection)
- Risk Classifier (4-axis scoring)
- Mentor quota enforcement (10 calls/day)
- Cost governor

### Phase 6: Memory System ✅
- Instruction ledger (CRUD)
- Pseudo-embeddings for semantic search
- Decision history tracking
- Memory caching (Redis + in-memory)
- Memory ↔ workflow integration

### Phase 7: Dashboard & Observability ✅
- Next.js 14 frontend with shadcn/ui
- 9 pages: Home, Tasks, Audit, Agents, Cost, Memory, Alerts, Workflow, Projects
- Real-time WebSocket updates
- OpenTelemetry tracing
- Prometheus metrics
- JSON structured logging
- Grafana dashboards
- 5 Prometheus alert rules

---

## Excluded from MVP

### Phase 8: Deployment & Operations
- Staging/production deployment pipeline
- Automated rollback
- Blue-green deployment
- Health checks and load balancing

### Phase 9: Optimization & Autonomy
- Multi-project support
- Self-improving agent prompts
- Automated performance tuning
- Advanced ML-based model selection

---

## MVP Success Criteria

| Criterion | Target |
|-----------|--------|
| End-to-end workflow | Task created → DONE without manual intervention |
| Verification pass rate | ≥ 80% of tasks pass verification on first attempt |
| Confidence score | Average confidence ≥ 0.70 |
| Law compliance | 0 critical law violations |
| Cost control | Average task cost < $0.05 |
| Response time | API p95 latency < 2 seconds |
| Test coverage | ≥ 70% code coverage |
| Uptime | ≥ 99% during testing |

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0 | 1-2 weeks | 2 weeks |
| Phase 1 | 2-3 weeks | 5 weeks |
| Phase 2 | 2-3 weeks | 8 weeks |
| Phase 3 | 2-4 weeks | 12 weeks |
| Phase 4 | 2-3 weeks | 15 weeks |
| Phase 5 | 2 weeks | 17 weeks |
| Phase 6 | 2-3 weeks | 20 weeks |
| Phase 7 | 2-3 weeks | 23 weeks |

**Total**: 8-23 weeks (depending on parallelization)

> **Note**: With parallel development, MVP can be delivered in 8-11 weeks.

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
