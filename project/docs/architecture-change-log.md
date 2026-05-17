# Architecture Change Log

## AI SDLC Orchestrator — Version History

---

## v5.0.0 (2026-05-17) — Phase 6 & 7 Complete

### Added
- **Phase 6: Memory System**
  - Instruction ledger with CRUD operations
  - Pseudo-embeddings for offline semantic search
  - Decision history tracking
  - Memory caching (Redis + in-memory fallback)
  - Memory ↔ workflow integration
  - Memory API router with search endpoint
- **Phase 7: Dashboard & Observability**
  - Next.js 14 frontend with shadcn/ui components
  - TailwindCSS 3 with custom theme + dark mode
  - 9 pages: Home, Tasks, Audit, Agents, Cost, Memory, Alerts, Workflow, Projects
  - Real-time WebSocket updates
  - OpenTelemetry distributed tracing
  - Prometheus metrics (task counts, cost, latency, retry rate, confidence)
  - JSON structured logging
  - Grafana dashboards with auto-provisioning
  - 5 Prometheus alert rules
  - Promtail log collector
  - Docker resource limits for all services
- **New services**: `services/memory/` (6 files), `shared/observability/` (3 files)
- **New routers**: `dashboard.py`, `governance.py`, `models.py`, `verification.py`
- **New components**: 11 UI components (Button, Card, Badge, Input, Table, Skeleton, Toast, etc.)
- **New scripts**: `scripts/start.sh`, `scripts/stop.sh`
- **Tests**: 478/478 pass (up from 38)

### Changed
- PostgreSQL image: `postgres:16` → `pgvector/pgvector:pg16`
- All SQLAlchemy Enum columns now use explicit `name` parameter to match schema.sql
- ThemeProvider: class-based dark mode for shadcn compatibility
- Toast system: migrated to Radix UI Toast

---

## v4.0.0 (2026-05-15) — Dynamic Model Router

### Added
- Dynamic Model Router (`shared/config/model_router.py`)
- Model capability registry (`shared/config/model_capabilities.yaml`)
- Pydantic settings (`shared/config/settings.py`)
- Optimistic locking (`shared/concurrency.py`)
- Retry service (`services/orchestrator/services/retry_service.py`)
- Audit service (`services/orchestrator/services/audit_service.py`)
- Confidence engine (`services/orchestrator/services/confidence_engine.py`)
- Risk classifier (`services/orchestrator/services/risk_classifier.py`)
- Law engine (`services/orchestrator/services/law_engine.py`)
- Mode selector (`services/orchestrator/services/mode_selector.py`)
- Validation service (`services/orchestrator/services/validation.py`)
- Verification service (`services/orchestrator/services/verification_service.py`)
- Auditor service (`services/orchestrator/services/auditor_service.py`)
- Mentor service (`services/orchestrator/services/mentor_service.py`)
- Rollback service (`services/orchestrator/services/rollback_service.py`)
- Circuit breaker (`shared/llm/circuit_breaker.py`)
- Retry handler (`shared/llm/retry_handler.py`)
- 13 Pydantic schema files in `shared/schemas/`
- 20 SQLAlchemy ORM models in `shared/models/`
- Alembic migrations
- 38 unit tests

### Changed
- Brain: OpenCode → FastAPI
- LLM calls: All via OpenCode → OpenCode + OpenCode
- State machine: 9 states → 11 states (+FAILED, +CANCELLED)
- Terminal states: 1 (DONE) → 3 (DONE, FAILED, CANCELLED)
- Dependencies: UUID[] array → Junction tables
- Auth: None → JWT + API Key
- Circuit breaker: None → Per-model
- Mentor quota: YAML config → Database-enforced
- Confidence: Could go negative → Clamped [0, 1]
- Laws: 12 → 20
- Prompt templates: 4 → 7

---

## v3.0.0 (2026-05-14) — FastAPI Migration

### Added
- FastAPI backend as central brain
- State transition rules (`shared/config/state_transitions.py`)
- Model configuration (`shared/config/models.yaml`)
- Database schema v2.0.0 (15+ tables)
- 15+ design documents in `docs/`
- 8 agent specs in `specs/`
- Docker Compose (PostgreSQL, Redis, API)
- OpenCode integration spec

### Changed
- Brain: Self-built → FastAPI
- OpenCode role: Central brain → LLM + Tool provider
- LLM config: Hardcoded → Environment variables
- Cost tracking: Basic → Per-call logging

---

## v2.0.0 (2026-05-13) — State Machine v2

### Added
- FAILED and CANCELLED states
- Junction tables for dependencies
- Embedding config table (configurable dimensions)
- LLM call logs table
- Circuit breaker state table
- Mentor quota table (database-enforced)
- Auth tables (users, api_keys)
- 20 architectural laws (up from 12)
- 7 prompt templates (up from 4)

### Changed
- States: 9 → 11
- Terminal states: 1 → 3
- ESCALATED→DONE: Only with verified output evidence
- Laws: 12 → 20
- Prompts: 4 → 7

---

## v1.0.0 (2026-05-12) — Initial Design

### Added
- Initial system design
- 9-state state machine
- 4 agent prompt templates
- 12 architectural laws
- 4 design documents

---

**Last Updated**: 2026-05-17
**Current Version**: 5.0.0
