# AI SDLC System

## AI Software Company Operating System

> Một hệ thống điều phối AI mô phỏng công ty phần mềm — người dùng chỉ mô tả nghiệp vụ, AI tự lo toàn bộ vòng đời sản phẩm. **OpenCode là bộ não** điều phối toàn bộ hệ thống.

---

## Tổng quan

Hệ thống được thiết kế để mô phỏng một công ty phần mềm dùng AI, trong đó người dùng chỉ cần mô tả nghiệp vụ, mục tiêu hoặc yêu cầu sản phẩm. Phần còn lại hệ thống sẽ tự động thực hiện theo quy trình chuẩn:

**Tiếp nhận → Phân tích → Thiết kế → Chia task → Triển khai → Kiểm tra → Deploy → Giám sát → Bảo trì**

### Nguyên lý cốt lõi
1. **FastAPI là bộ não** — Điều phối toàn bộ: state machine, workflow engine, agent dispatch, cost tracking, audit logging
2. **OpenCode là tích hợp** — Cung cấp LLM models và tool execution (bash, edit, write, read, glob, grep)
3. **Model chuyên biệt** — Mỗi model phục vụ một thế mạnh riêng
4. **Workflow theo trạng thái** — 11 states (3 terminal), 22 valid transitions
5. **Dual-model validation** — Gatekeeper + Validator cross-validate trước khi pass task
6. **Có lớp quản trị** — Mọi output đều qua luật (20 laws), ngưỡng tin cậy, kiểm tra
7. **Có bộ nhớ ngoài** — AI đọc trạng thái từ database
8. **Có cơ chế kiểm chứng** — Chỉ tin kết quả chạy thật trong sandbox
9. **Có resilience** — Circuit breaker, retry với backoff, fallback model

### FastAPI-Centric Architecture
- **FastAPI (Brain)**: Điều phối toàn bộ workflow, state machine, agent dispatch
- **State Machine**: 11 states, 3 terminal states (DONE, FAILED, CANCELLED)
- **LLM Gateway**: Circuit breaker, retry, fallback, cost tracking cho mọi LLM call
  - Path 1: LiteLLM trực tiếp (Gatekeeper, Orchestrator, Mentor, Monitoring)
  - Path 2: OpenCode integration (Specialist, Auditor, DevOps)
- **Execution (Dev)**: OpenCode tools (bash, edit, write, read, glob, grep)
- **Execution (Prod)**: Docker sandbox (isolated container)

---

## Cấu trúc thư mục

```
project/
├── governance/
│   └── laws.yaml                    # 20 architectural laws (v3)
├── database/
│   └── schema.sql                   # PostgreSQL schema (15+ tables, v2.0.0)
├── docs/
│   ├── dynamic-model-router.md      # v4 Dynamic Model Router design
│   ├── state-machine.md             # Workflow state machine (v2)
│   ├── agent-matrix.md              # Agent responsibility matrix
│   ├── opencode-architecture.md     # OpenCode integration design (v3)
│   ├── security-design.md           # Auth, RBAC, API security
│   ├── error-handling-resilience.md # Circuit breaker, retry, fallback
│   ├── llm-integration.md           # LLM call management (v3)
│   ├── database-migration.md        # Alembic migration strategy
│   ├── api-specification.md         # REST API design
│   ├── testing-strategy.md          # Testing approach
│   ├── non-functional-requirements.md # NFRs
│   ├── mvp-scope.md                 # Trimmed MVP definition
│   ├── llm-observability.md         # LLM metrics, cost tracking
│   ├── risk-assessment.md           # Risks and mitigations
│   ├── data-flow.md                 # Data flow diagrams (v3)
│   └── architecture-change-log.md   # v2 → v3 change log
├── specs/
│   ├── gatekeeper.yaml              # Gatekeeper agent spec
│   ├── orchestrator.yaml            # Orchestrator agent spec
│   ├── specialist.yaml              # Specialist agent spec
│   ├── auditor.yaml                 # Auditor agent spec
│   ├── mentor.yaml                  # Mentor agent spec
│   ├── devops.yaml                  # DevOps agent spec
│   ├── monitoring.yaml              # Monitoring agent spec
│   └── opencode_integration.yaml    # OpenCode integration spec (v3)
├── agents/
│   └── prompts/                     # 7 prompt templates
├── shared/
│   ├── config/
│   │   ├── settings.py              # [NEW] Pydantic settings
│   │   ├── models.yaml              # Model config (v4, 5 models)
│   │   ├── model_capabilities.yaml  # [NEW] Capability registry
│   │   ├── model_router.py          # [NEW] Dynamic router
│   │   └── state_transitions.py     # State transition rules (22 transitions)
│   ├── models/                      # [NEW] SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── module.py
│   │   ├── task.py
│   │   └── registry.py              # All other models
│   ├── schemas/                     # [NEW] Pydantic schemas
│   │   ├── project.py
│   │   ├── module.py
│   │   ├── task.py
│   │   └── validation.py            # [NEW] Validation gate schemas
│   ├── database.py                  # [NEW] Async DB engine, session
│   └── cache.py                     # [NEW] Redis cache integration
├── services/
│   ├── orchestrator/                # [NEW] FastAPI backend (Phase 1)
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── routers/                 # [NEW] API routers
│   │   │   ├── projects.py
│   │   │   ├── modules.py
│   │   │   ├── tasks.py
│   │   │   └── validation.py        # [NEW] Validation gate API
│   │   ├── services/                # [NEW] Business logic
│   │   │   ├── projects.py
│   │   │   ├── modules.py
│   │   │   ├── tasks.py
│   │   │   └── validation.py        # [NEW] Validation gate service
│   │   └── middleware/              # [NEW] Middleware
│   │       └── audit.py
│   ├── execution/                   # Execution layer (Phase 4)
│   └── memory/                      # Memory system (Phase 6)
├── apps/
│   └── dashboard/                   # Next.js frontend (Phase 7)
├── alembic/                         # [NEW] Database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
├── tests/                           # [NEW] Unit tests
│   ├── test_state_transitions.py
│   ├── test_schemas.py
│   ├── test_services.py
│   └── test_model_router.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── ARCHITECTURE.md                  # Architecture overview (v3)
└── README.md                        # This file (v3)
```

---

## 7 Agents (OpenCode Tools per Agent)

| Agent | Vai trò | Model | OpenCode Tools |
|---|---|---|---|
| **Gatekeeper** | Cổng đầu vào, phân loại, routing | DeepSeek V4 Flash | read, glob, grep |
| **Orchestrator** | Điều phối, chia task, chọn agent | Qwen 3.6 Plus | read, glob, grep |
| **Specialist** | Viết code, thực thi | DeepSeek V4 Pro | bash, edit, write, read, glob, grep |
| **Auditor** | Review, kiểm định, compliance | Qwen 3.5 Plus | bash (tests), read, glob, grep |
| **Mentor** | Xử lý deadlock, quyết định chiến lược | Qwen 3.6 Plus | read, glob, grep |
| **DevOps** | Build, deploy, rollback | DeepSeek V4 Pro | bash, read |
| **Monitoring** | Giám sát, alert | DeepSeek V4 Flash | bash, read |

---

## Workflow State Machine (v2)

```
NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE ✅
  │       │          │            │             │            │
  │       │          │            │             │            └─ Auditor approve
  │       │          │            │             └─ Sandbox pass/fail
  │       │          │            └─ Code hoàn thành
  │       │          └─ Agent nhận task
  │       └─ Orchestrator chia task
  └─ Gatekeeper phân loại

Special states:
  ESCALATED → Mentor takeover → PLANNING (retry)
  ESCALATED → Mentor reject → FAILED ✗
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
| Database | PostgreSQL, pgvector |
| Cache/Queue | Redis |
| ORM | SQLAlchemy (async) |
| Validation | Pydantic |
| Migrations | Alembic |
| Auth | JWT + API Key |
| LLM Gateway | LiteLLM + OpenCode |
| Execution (Dev) | OpenCode tools |
| Execution (Prod) | Docker |
| Frontend | Next.js, TailwindCSS, Recharts |
| Monitoring | Prometheus, Loki, Grafana |
| LLMs | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus |
| Embeddings | Configurable (OpenAI/BGE) via embedding_config table |

---

## Key Changes from v1

| Aspect | v1 | v2 | v3 |
|---|---|---|---|
| Brain | Self-built orchestration | **OpenCode** | **FastAPI** |
| OpenCode role | — | Brain | **LLM + Tool Provider** |
| LLM calls | — | All via OpenCode | **LiteLLM + OpenCode** |
| States | 9 states, 1 terminal | **11 states, 3 terminals** | 11 states, 3 terminals |
| Dependencies | UUID[] array | **Junction tables** | Junction tables |
| Auth | None | **JWT + API Key** | JWT + API Key |
| LLM config | Hardcoded endpoints | **Environment variables** | Environment variables |
| Circuit breaker | None | **Per-model circuit breaker** | Per-model circuit breaker |
| Mentor quota | Config only | **Database-enforced** | Database-enforced |
| Confidence | Could go negative | **Clamped [0,1]** | Clamped [0,1] |
| Cost tracking | Basic | **Per-call logging** | Per-call logging |
| Laws | 12 | **20 laws** | 20 laws |
| Prompts | 4 templates | **7 templates** | 7 templates |
| Design docs | 4 | **15+ docs** | 16+ docs |

---

## Phases

| Phase | Tên | Thời gian | Trạng thái |
|---|---|---|---|
| 0 | System Design | 1-2 tuần | ✅ Complete (v4) |
| 1 | Core State System | 2-3 tuần | 🟡 Partial (60%) |
| 2 | Workflow Engine | 2-3 tuần | ⬜ Pending |
| 3 | Agent Runtime | 2-4 tuần | ⬜ Pending |
| 4 | Verification Sandbox | 2-3 tuần | ⬜ Pending |
| 5 | Governance Layer | 2 tuần | ⬜ Pending |
| 6 | Memory System | 2-3 tuần | ⬜ Pending |
| 7 | Dashboard & Observability | 2-3 tuần | ⬜ Pending |
| 8 | Deployment & Operations | 2-3 tuần | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | ⬜ Pending |

### MVP (8-11 weeks)
Phases 0-4 only — prove the core workflow works end-to-end. See `docs/mvp-scope.md` for details.

---

## Quick Start (Phase 1)

```bash
# 1. Clone và setup
cd project

# 2. Tạo database
psql -c "CREATE DATABASE ai_sdlc;"
psql -d ai_sdlc -f database/schema.sql

# 3. Setup Python environment
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2 pydantic redis alembic

# 4. Setup environment variables
cp .env.example .env
# Edit .env with your API keys and database URL

# 5. Run (Phase 1)
uvicorn services.orchestrator.main:app --reload
```

---

## Documentation Index

### Core Design
- [Architecture Documentation](./ARCHITECTURE.md)
- [State Machine](./docs/state-machine.md)
- [Agent Matrix](./docs/agent-matrix.md)
- [OpenCode Architecture](./docs/opencode-architecture.md)
- [Laws](./governance/laws.yaml)
- [Database Schema](./database/schema.sql)
- [Model Configuration](./shared/config/models.yaml)
- [State Transitions](./shared/config/state_transitions.py)

### Design Documents (New in v2)
- [Security Design](./docs/security-design.md)
- [Error Handling & Resilience](./docs/error-handling-resilience.md)
- [LLM Integration](./docs/llm-integration.md)
- [Database Migration](./docs/database-migration.md)
- [API Specification](./docs/api-specification.md)
- [Testing Strategy](./docs/testing-strategy.md)
- [Non-Functional Requirements](./docs/non-functional-requirements.md)
- [MVP Scope](./docs/mvp-scope.md)
- [LLM Observability](./docs/llm-observability.md)
- [Risk Assessment](./docs/risk-assessment.md)
- [Data Flow](./docs/data-flow.md)

### Task Breakdown
- [Task Index](../tasks/README.md)

---

**Version**: 4.4.0
**Created**: 2026-05-14
**Status**: Phase 0 Complete (v4), Phase 1 Partial (95%) — FastAPI CRUD APIs, ORM, Alembic, Redis, Validation Gate, Risk Mitigations, Retry/Audit Services, Integration Tests
**Phase 1 Progress**: 48+ files created, 70+ tests (45 unit + 25+ integration), CRUD APIs for Projects/Modules/Tasks/Validation/Retry/Audit
**v4.1 Change**: Added Dual-Model Validation Gate — cross-validation before NEW → ANALYZING transition
**v4.2 Change**: Fixed 3 critical risks — State Bloat (optimistic locking), Context Window (priority truncation + Lost in the Middle), Dependency Blocked (timeout + notifications)
**v4.3 Change**: Added Retry Tracking Service (max retries, can_retry, stats) + Audit Service (query logs, CSV export)
**v4.4 Change**: Added 25+ integration tests — E2E workflow: Projects → Modules → Tasks → Transitions → Validation → Retry/Audit