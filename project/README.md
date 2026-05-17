# AI SDLC Orchestrator

## AI Software Company Operating System

> Một hệ thống điều phối AI mô phỏng công ty phần mềm — người dùng chỉ mô tả nghiệp vụ, AI tự lo toàn bộ vòng đời sản phẩm. **FastAPI là bộ não** điều phối toàn bộ hệ thống.

---

## Tổng quan

Hệ thống được thiết kế để mô phỏng một công ty phần mềm dùng AI, trong đó người dùng chỉ cần mô tả nghiệp vụ, mục tiêu hoặc yêu cầu sản phẩm. Phần còn lại hệ thống sẽ tự động thực hiện theo quy trình chuẩn:

**Tiếp nhận → Phân tích → Thiết kế → Chia task → Triển khai → Kiểm tra → Deploy → Giám sát → Bảo trì**

### Nguyên lý cốt lõi
1. **FastAPI là bộ não** — Điều phối toàn bộ: state machine, workflow engine, agent dispatch, cost tracking, audit logging
2. **LLM Gateway** — OpenCodecho simple calls,OpenCode integration cho coding tasks
3. **Model chuyên biệt** — Dynamic Model Router chọn model dựa trên complexity, risk, domain
4. **Workflow theo trạng thái** — 11 states (3 terminal), 22 valid transitions
5. **Có lớp quản trị** — Mọi output đều qua luật (20 laws), ngưỡng tin cậy, kiểm tra
6. **Có bộ nhớ ngoài** — AI đọc trạng thái từ database, pgvector cho semantic search
7. **Có cơ chế kiểm chứng** — 5-step pipeline: lint → unit test → integration test → build → security scan
8. **Có resilience** — Circuit breaker, retry với backoff, fallback model, rollback engine

### FastAPI-Centric Architecture
- **FastAPI (Brain)**: Điều phối toàn bộ workflow, state machine, agent dispatch
- **State Machine**: 11 states, 3 terminal states (DONE, FAILED, CANCELLED)
- **LLM Gateway**: Dynamic Model Router, Circuit breaker, retry, fallback, cost tracking
- **Verification Pipeline**: 5 bước tự động (lint, test, build, security)
- **Execution (Dev)**:OpenCode tools (bash, edit, write, read, glob, grep)
- **Execution (Prod)**: Docker sandbox (isolated container)

---

## Cấu trúc thư mục

```
project/
├── governance/
│   └── laws.yaml                    # 20 architectural laws
├── database/
│   └── schema.sql                   # PostgreSQL schema (20 tables, v2.0.0)
├── docs/                            # 16 design documents
│   ├── agent-matrix.md
│   ├── api-specification.md
│   ├── architecture-change-log.md
│   ├── data-flow.md
│   ├── database-migration.md
│   ├── dynamic-model-router.md
│   ├── error-handling-resilience.md
│   ├── llm-integration.md
│   ├── llm-observability.md
│   ├── mvp-scope.md
│   ├── non-functional-requirements.md
│   ├── opencode-architecture.md
│   ├── risk-assessment.md
│   ├── security-design.md
│   ├── state-machine.md
│   └── testing-strategy.md
├── specs/                           # 8 agent specs (YAML)
│   ├── gatekeeper.yaml
│   ├── orchestrator.yaml
│   ├── specialist.yaml
│   ├── coder.yaml
│   ├── auditor.yaml
│   ├── reviewer.yaml
│   ├── mentor.yaml
│   ├── devops.yaml
│   └── monitoring.yaml
├── agents/
│   └── prompts/                     # 10 prompt templates
│       ├── gatekeeper.txt
│       ├── orchestrator.txt
│       ├── specialist.txt (= coder.txt)
│       ├── coder.txt (= specialist.txt)
│       ├── auditor.txt (= reviewer.txt)
│       ├── reviewer.txt (= auditor.txt)
│       ├── mentor.txt
│       ├── devops.txt
│       ├── monitoring.txt
│       └── validator.txt
├── shared/
│   ├── config/
│   │   ├── settings.py              # Pydantic settings
│   │   ├── models.yaml              # Model config (4 models)
│   │   ├── model_capabilities.yaml  # Capability registry
│   │   ├── model_router.py          # Dynamic Model Router
│   │   └── state_transitions.py     # 22 valid transitions
│   ├── models/                      # SQLAlchemy ORM models (20 tables)
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── module.py
│   │   ├── task.py                  # TaskStatus, TaskPriority, RiskLevel
│   │   ├── registry.py              # Retry, AuditLog, MentorInstruction, etc.
│   │   └── law.py                   # LawViolation, LawSeverity
│   ├── schemas/                     # Pydantic request/response schemas (13 files)
│   │   ├── audit.py
│   │   ├── confidence.py
│   │   ├── cost.py
│   │   ├── decision.py
│   │   ├── law.py
│   │   ├── mentor_instruction.py
│   │   ├── module.py
│   │   ├── project.py
│   │   ├── retry.py
│   │   ├── risk.py
│   │   ├── task.py
│   │   └── verification.py
│   ├── database.py                  # Async DB engine, session factory
│   ├── cache.py                     # Redis cache with in-memory fallback
│   ├── concurrency.py               # Optimistic locking
│   ├── llm/
│   │   ├── circuit_breaker.py       # 3-state circuit breaker
│   │   └── retry_handler.py         # Exponential backoff
│   └── observability/               # Phase 7
│       ├── tracing.py               # OpenTelemetry tracing
│       ├── metrics.py               # Prometheus metrics
│       └── logging.py               # JSON structured logging
├── services/
│   ├── orchestrator/                # FastAPI backend
│   │   ├── main.py                  # FastAPI app entry + lifespan
│   │   ├── routers/                 # API routers (8 routers)
│   │   │   ├── projects.py
│   │   │   ├── modules.py
│   │   │   ├── tasks.py
│   │   │   ├── dashboard.py         # Summary, WebSocket, aggregation
│   │   │   ├── audit_logs.py
│   │   │   ├── governance.py        # Laws, violations, scan
│   │   │   ├── models.py            # Model selection, capabilities
│   │   │   └── verification.py      # Verify pipeline, rollback
│   │   ├── services/                # Business logic (15+ services)
│   │   │   ├── projects.py
│   │   │   ├── modules.py
│   │   │   ├── tasks.py
│   │   │   ├── workflow_engine.py   # State machine execution
│   │   │   ├── verification_service.py  # 5-step pipeline
│   │   │   ├── auditor_service.py   # 5-dimension review
│   │   │   ├── mentor_service.py    # Strategic decisions
│   │   │   ├── risk_classifier.py   # 4-axis risk scoring
│   │   │   ├── confidence_engine.py # TLPA confidence formula
│   │   │   ├── law_engine.py        # 20 laws enforcement
│   │   │   ├── mode_selector.py     # Dev/prod mode selection
│   │   │   ├── validation.py        # Gatekeeper cross-validation
│   │   │   ├── audit_service.py     # Audit log CRUD
│   │   │   ├── retry_service.py     # Retry tracking (max 2)
│   │   │   └── rollback_service.py  # Git revert, snapshot restore
│   │   └── middleware/
│   │       └── audit.py             # API request logging + WebSocket broadcast
│   ├── execution/
│   │   └── opencode_verification.py # Dev-mode verification tools
│   └── memory/                      # Phase 6 Memory System
│       ├── ledger.py                # Instruction ledger
│       ├── embedding.py             # Pseudo-embeddings + semantic search
│       ├── decision.py              # Decision history
│       ├── cache.py                 # Memory caching
│       ├── integration.py           # Memory ↔ workflow integration
│       └── router.py                # Memory API router
├── apps/
│   └── dashboard/                   # Phase 7 Next.js frontend (shadcn/ui)
│       ├── src/
│       │   ├── app/                 # 9 pages (home, tasks, audit, agents, cost, memory, alerts, workflow, projects)
│       │   ├── components/          # Sidebar, Header, StatCard, Breadcrumbs, ErrorBoundary, AlertBanner, ui/*
│       │   ├── lib/                 # api.ts, hooks.tsx, toast.tsx, theme.tsx, utils.ts, websocket.ts
│       │   ├── stores/              # Zustand stores
│       │   └── types/               # TypeScript types
│       ├── tailwind.config.ts       # shadcn theme + custom colors
│       └── package.json
├── docker/
│   └── monitoring/                  # Prometheus, Loki, Promtail, Grafana
│       ├── docker-compose.monitoring.yml
│       ├── prometheus/              # prometheus.yml, alerts.yml (5 rules)
│       ├── loki/                    # loki-config.yml
│       ├── promtail/                # promtail-config.yml
│       └── grafana/                 # datasources, dashboards
├── docker-compose.yml               # PostgreSQL (pgvector), Redis, API
├── scripts/
│   ├── start.sh                     # One-command startup
│   └── stop.sh                      # Stop all services
├── tests/                           # 478 unit tests (all pass)
│   ├── test_state_transitions.py
│   ├── test_schemas.py
│   ├── test_services.py
│   ├── test_model_router.py
│   ├── test_verification.py
│   ├── test_confidence.py
│   ├── test_law_engine.py
│   ├── test_memory.py
│   ├── test_observability.py
│   └── test_dashboard.py
├── alembic/                         # Database migrations
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
└── README.md
```

---

## 10 Agents (Prompt Templates)

| Agent | Vai trò | Model Preference | Tools |
|---|---|---|---|
| **Gatekeeper** | Cổng đầu vào, phân loại complexity, routing | DeepSeek V4 Flash | read, glob, grep |
| **Orchestrator** | Điều phối, chia task, chọn agent | Qwen 3.6 Plus | read, glob, grep |
| **Validator** | Cross-validate Gatekeeper classification | Qwen 3.5 Plus | read, glob, grep |
| **Specialist** | Viết code, thực thi | DeepSeek V4 Pro | bash, edit, write, read, glob, grep |
| **Auditor** | Review 5 dimensions, kiểm định compliance | Qwen 3.5 Plus | bash (tests), read, glob, grep |
| **Mentor** | Xử lý deadlock, quyết định chiến lược | Qwen 3.6 Plus | read, glob, grep |
| **DevOps** | Build, deploy, rollback | DeepSeek V4 Pro | bash, read |
| **Monitoring** | Giám sát, alert, metrics | DeepSeek V4 Flash | bash, read |

> **Note:** `coder.txt` = `specialist.txt` (duplicate), `reviewer.txt` = `auditor.txt` (duplicate). `validator.txt` là agent thứ 8 — cross-validate Gatekeeper classification.

---

## Workflow State Machine (v2)

```
NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE ✅
  │       │          │            │             │            │
  │       │          │            │             │            └─ Auditor approve (≥0.80)
  │       │          │            │             └─ 5-step pipeline (score ≥60)
  │       │          │            └─ Code hoàn thành
  │       │          └─ Agent nhận task
  │       └─ Orchestrator chia task
  └─ Gatekeeper phân loại

Special states:
  ESCALATED → Mentor takeover → PLANNING (retry) hoặc FAILED (reject)
  BLOCKED → Dependency resolved → PLANNING

Terminal states (immutable):
  DONE ✅       — Task hoàn thành thành công
  FAILED ✗     — Task thất bại vĩnh viễn
  CANCELLED ✗  — Task bị hủy bởi user
```

---

## Tech Stack

| Thành phần | Tech |
|---|---|
| Brain orchestration | Python, FastAPI |
| State machine | Python, FastAPI |
| Backend API | FastAPI |
| Database | PostgreSQL 16, pgvector |
| Cache/Queue | Redis 7 |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic |
| Migrations | Alembic |
| Auth | JWT + API Key |
| LLM Gateway |OpenCode |
| Execution (Dev) |OpenCode tools |
| Execution (Prod) | Docker sandbox |
| Frontend | Next.js 14, TailwindCSS 3, shadcn/ui, Recharts, Zustand, Framer Motion |
| Monitoring | Prometheus, Loki, Promtail, Grafana, OpenTelemetry |
| LLMs | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus |
| Embeddings | Configurable (OpenAI/BGE) via embedding_config table |

---

## Key Changes from v1

| Aspect | v1 | v2 | v3-v4 |
|---|---|---|---|
| Brain | Self-built orchestration | **OpenCode** | **FastAPI** |
|OpenCode role | — | Brain | **LLM + Tool Provider** |
| LLM calls | — | All viaOpenCode | **OpenCode** |
| Model routing | Fixed assignments | Fixed | **Dynamic Model Router** |
| States | 9 states, 1 terminal | **11 states, 3 terminals** | 11 states, 3 terminals |
| Dependencies | UUID[] array | **Junction tables** | Junction tables |
| Auth | None | **JWT + API Key** | JWT + API Key |
| Circuit breaker | None | **Per-model circuit breaker** | Per-model circuit breaker |
| Mentor quota | Config only | **Database-enforced** | Database-enforced |
| Confidence | Could go negative | **Clamped [0,1]** | Clamped [0,1] |
| Cost tracking | Basic | **Per-call logging** | Per-call logging |
| Laws | 12 | **20 laws** | 20 laws |
| Prompts | 4 templates | **7 templates** | 10 templates |
| Design docs | 4 | **15+ docs** | 16 docs |
| Memory | — | — | **Phase 6: ledger, embedding, decision** |
| Dashboard | — | — | **Phase 7: Next.js + shadcn/ui** |
| Observability | — | — | **Phase 7: OpenTelemetry, Prometheus, Grafana** |

---

## Phases

| Phase | Tên | Thời gian | Trạng thái |
|---|---|---|---|
| 0 | System Design | 1-2 tuần | ✅ Complete (v4) |
| 1 | Core State System | 2-3 tuần | ✅ Complete (CRUD APIs, ORM, Alembic, Redis) |
| 2 | Workflow Engine | 2-3 tuần | ✅ Complete (state machine, node execution, retries) |
| 3 | Agent Runtime | 2-4 tuần | ✅ Complete (10 agents, prompts, LLM gateway) |
| 4 | Verification Sandbox | 2-3 tuần | ✅ Complete (5-step pipeline, dev/prod modes) |
| 5 | Governance Layer | 2 tuần | ✅ Complete (confidence, laws, risk, cost) |
| 6 | Memory System | 2-3 tuần | ✅ Complete (ledger, embedding, decision, cache) |
| 7 | Dashboard & Observability | 2-3 tuần | ✅ Complete (Next.js + shadcn/ui, Prometheus, Grafana) |
| 8 | Deployment & Operations | 2-3 tuần | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | ⬜ Pending |

### MVP (8-11 weeks)
Phases 0-7 — prove the core workflow works end-to-end with full observability.

---

## Quick Start

```bash
cd project

# Option 1: One-command startup (recommended)
./scripts/start.sh

# Option 2: Manual
# 1. Start PostgreSQL + Redis
docker compose up -d postgres redis

# 2. Run database schema
docker cp database/schema.sql project-postgres-1:/tmp/schema.sql
docker exec -i project-postgres-1 psql -U ai_sdlc_user -d ai_sdlc -f /tmp/schema.sql

# 3. Start backend
PYTHONPATH=$PWD uvicorn services.orchestrator.main:app --reload --port 8000

# 4. Start frontend (new terminal)
cd apps/dashboard && npm run dev
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |

---

## Documentation Index

### Core Design
- [Architecture Documentation](./ARCHITECTURE.md)
- [State Machine](./docs/state-machine.md)
- [Agent Matrix](./docs/agent-matrix.md)
- [OpenCode Architecture](./docs/opencode-architecture.md)
- [Dynamic Model Router](./docs/dynamic-model-router.md)
- [Laws](./governance/laws.yaml)
- [Database Schema](./database/schema.sql)
- [Model Configuration](./shared/config/models.yaml)
- [State Transitions](./shared/config/state_transitions.py)

### Design Documents
- [Security Design](./docs/security-design.md)
- [Error Handling & Resilience](./docs/error-handling-resilience.md)
- [LLM Integration](./docs/llm-integration.md)
- [LLM Observability](./docs/llm-observability.md)
- [Database Migration](./docs/database-migration.md)
- [API Specification](./docs/api-specification.md)
- [Testing Strategy](./docs/testing-strategy.md)
- [Non-Functional Requirements](./docs/non-functional-requirements.md)
- [MVP Scope](./docs/mvp-scope.md)
- [Risk Assessment](./docs/risk-assessment.md)
- [Data Flow](./docs/data-flow.md)
- [Architecture Change Log](./docs/architecture-change-log.md)

---

**Version**: 5.0.0
**Created**: 2026-05-14
**Last Updated**: 2026-05-17
**Status**: Phases 0-7 Complete, Phase 8 Pending
**Tests**: 478/478 pass
**Frontend**: Next.js 14 + shadcn/ui + TailwindCSS 3
