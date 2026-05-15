# ARCHITECTURE - AI SDLC System

## AI Software Company Operating System

---

## 1. Tổng quan

Hệ thống điều phối AI SDLC mô phỏng một công ty phần mềm dùng AI, trong đó người dùng chỉ cần mô tả nghiệp vụ, mục tiêu hoặc yêu cầu sản phẩm. Phần còn lại hệ thống tự động thực hiện theo quy trình chuẩn của một đội ngũ kỹ thuật chuyên nghiệp.

### Mục tiêu
- Tiếp nhận yêu cầu → Phân tích → Thiết kế → Chia task → Triển khai → Kiểm tra → Deploy → Giám sát → Bảo trì
- Không phải một AI làm mọi thứ mơ hồ, mà là hệ thống có quy trình, phân vai, luật lệ, kiểm chứng và khả năng học

### Nguyên lý cốt lõi
1. **FastAPI là bộ não** — Điều phối toàn bộ: state machine, workflow engine, agent dispatch, cost tracking, audit logging
2. **OpenCode là tích hợp** — Cung cấp LLM models và tool execution (bash, edit, write, read, glob, grep)
3. **Model chuyên biệt** — Mỗi model phục vụ một thế mạnh riêng
4. **Workflow theo trạng thái** — Mọi task đi qua các trạng thái rõ ràng (11 states, 3 terminal)
5. **Có lớp quản trị** — Mọi output đều qua luật, ngưỡng tin cậy, kiểm tra
6. **Có bộ nhớ ngoài** — AI đọc trạng thái từ database, không nhớ bằng cảm giác
7. **Có cơ chế kiểm chứng** — Chỉ tin kết quả chạy thật trong sandbox
8. **Có fallback và resilience** — Circuit breaker, retry với backoff, fallback model

---

## 2. Kiến trúc tổng thể

### FastAPI-Centric Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                           USER                                    │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (BRAINS)                         │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │State Machine│  │Workflow     │  │   Agent Router          │ │
│  │  Engine     │  │  Engine     │  │   & Dispatcher          │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────────┘ │
│         └────────────────┼────────────────────┘                │
│                          │                                       │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │                LLM Gateway                                  │  │
│  │  ┌──────────┐  ┌───────────┐  ┌───────────┐             │  │
│  │  │ Circuit  │  │   Retry   │  │   Cost    │             │  │
│  │  │ Breaker  │  │  w/ Backoff│  │ Tracker  │             │  │
│  │  └──────────┘  └───────────┘  └───────────┘             │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │              Agent Runtime                                  │  │
│  │  Gatekeeper | Orchestrator | Specialist | Auditor        │  │
│  │  Mentor | DevOps | Monitoring                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Execution Layer                                │  │
│  │  Dev Mode: OpenCode tools (bash, edit, write, read)      │  │
│  │  Prod Mode: Docker sandbox (isolated)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │  PostgreSQL  │  │    Redis     │  │   LLM APIs    │
   │ (State,     │  │  (Cache,    │  │ (via OpenCode │
   │  Audit,     │  │  Rate Limit)│  │  or LiteLLM)  │
   │  Memory,    │  └──────────────┘  └──────────────┘
   │  Embeddings)│
   └──────────────┘
```

### Execution Flow

```
1. User → FastAPI receives request (POST /api/v1/tasks)
2. FastAPI → Gatekeeper agent (via LLM Gateway → LiteLLM)
3. FastAPI → Validator agent (via LLM Gateway → LiteLLM) — NEW: Dual-model validation
4. FastAPI → Validation decision: APPROVED → Orchestrator | REJECTED → Re-analyze | MISMATCH → Mentor
5. FastAPI → Orchestrator agent (via LLM Gateway → LiteLLM)
6. FastAPI → State Machine (validate transition, update DB)
7. FastAPI → Specialist agent (via LLM Gateway → OpenCode for code + tools)
8. FastAPI → Verification (run lint/test/build via OpenCode bash tool)
9. FastAPI → Auditor agent (via LLM Gateway → LiteLLM or OpenCode)
10. FastAPI → Governance (confidence score, law check)
11. FastAPI → State Machine (update status in DB)
12. FastAPI → Memory (store lesson learned in PostgreSQL)
```

---

## 3. 5 Lớp chính

### 3.1. FastAPI Brain Layer
- **State machine engine**: Validate và thực thi 23 state transitions
- **Workflow engine**: Điều phối task lifecycle từ NEW → DONE
- **Dual-model validation gate**: Cross-validate Gatekeeper classification trước khi pass to Orchestrator
- **Agent router**: Dispatch agents dựa trên task type và complexity
- **LLM Gateway**: Circuit breaker, retry, fallback, cost tracking cho mọi LLM call
- **Audit logging**: Log mọi action với actor, timestamp, result

### 3.2. State Machine Layer
- **11 states**: NEW, ANALYZING, PLANNING, IMPLEMENTING, VERIFYING, REVIEWING, DONE, ESCALATED, BLOCKED, FAILED, CANCELLED
- **23 valid transitions** với điều kiện
- **3 terminal states**: DONE, FAILED, CANCELLED
- **State validation**: Mọi transition được validate trước khi thực thi
- **Audit logging**: Mọi state change được log với actor, reason, timestamp

### 3.3. Governance Layer
- **20 architectural laws** enforcement
- **Confidence scoring**: Confidence = clamp(T*0.35 + L*0.15 - P*0.20 + A*0.30, 0, 1)
- **Cost governor**: Giới hạn token usage, mentor calls
- **Risk classification**: LOW/MEDIUM/HIGH/CRITICAL
- **Mentor quota**: 10 calls/day, enforced via database

### 3.4. Verification Layer (Hybrid)
- **Dev mode**: OpenCode bash tool (lint, test, build) — nhanh, iteration
- **Production mode**: Docker container isolated — an toàn, reproducible
- **Pipeline**: Lint → Unit Test → Integration Test → Build → Security Scan
- **Rollback**: Auto rollback khi verification fail

### 3.5. Memory Layer
- **Instruction ledger**: Lưu mentor advice, failed patterns, decisions
- **Semantic retrieval**: pgvector với cosine similarity, configurable dimensions
- **Decision history**: Lưu quyết định kiến trúc, lý do
- **Lesson learned**: Bài học rút ra sau mỗi task

---

## 4. Workflow State Machine

```
NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
  │       │          │            │             │            │
  │       │          │            │             │            └─ Auditor approve
  │       │          │            │             └─ Sandbox pass / fail (retry)
  │       │          │            └─ Code hoàn thành
  │       │          └─ Agent nhận task
  │       └─ Orchestrator chia task
  └─ Gatekeeper phân loại

Terminal states:
  DONE       — Task hoàn thành thành công
  FAILED     — Task thất bại vĩnh viễn (Mentor reject, fatal error)
  CANCELLED  — Task hủy bởi user

Special states:
  ESCALATED  — Mentor takeover khi retry > 2
  BLOCKED    — Chờ đợi dependency
```

---

## 5. Agent Architecture

### FastAPI as the Brain
FastAPI điều phối toàn bộ agent lifecycle:
1. **Prompt loading**: Load template từ `/agents/prompts/*.txt`
2. **Context building**: Assemble task context (spec, modules, memory, laws)
3. **LLM call**: Through LLM Gateway (circuit breaker + cost tracking)
   - Path 1: LiteLLM trực tiếp (Gatekeeper, Orchestrator, Mentor, Monitoring)
   - Path 2: OpenCode integration (Specialist, Auditor, DevOps)
4. **Result parsing**: Parse JSON output từ agent
5. **Tool execution**: Execute code changes via OpenCode tools
6. **State transition**: Update task status trong state machine

### 7 Agents

| Agent | Vai trò | Model | LLM Path | OpenCode Tools |
|---|---|---|---|---|
| **Gatekeeper** | Phân loại, routing | DeepSeek V4 Flash | LiteLLM | — |
| **Orchestrator** | Điều phối, chia task | Qwen 3.6 Plus | LiteLLM | — |
| **Specialist** | Viết code, thực thi | DeepSeek V4 Pro | OpenCode | bash, edit, write, read, glob, grep |
| **Auditor** | Review, kiểm định | Qwen 3.5 Plus | LiteLLM | read, glob, grep |
| **Mentor** | Quyết định chiến lược | Qwen 3.6 Plus | LiteLLM | — |
| **DevOps** | Build, deploy, rollback | DeepSeek V4 Pro | OpenCode | bash, read |
| **Monitoring** | Giám sát, alert | DeepSeek V4 Flash | LiteLLM | — |

### Tool Restrictions per Agent
- **Specialist**: Full access (bash, edit, write, read, glob, grep) — cần viết code
- **Auditor**: Read-only + bash (chỉ chạy tests) — không sửa code
- **Gatekeeper/Orchestrator/Mentor**: Không cần tools — chỉ phân tích, điều phối
- **DevOps**: bash + read — build và deploy
- **Monitoring**: Không cần tools — chỉ quan sát, báo cáo

---

## 6. Resilience & Error Handling

### Circuit Breaker
- Mỗi LLM model có circuit breaker riêng
- **Closed**: Bình thường, gọi API
- **Open**: 5 lỗi liên tiếp → chuyển sang fallback model, chờ 30-90s
- **Half-Open**: Thử 3 calls, nếu thành công → Closed lại

### Retry with Exponential Backoff
- Max 3 retries cho LLM API calls
- Backoff: 1s → 2s → 4s
- Retryable: timeout, rate_limit, server_error
- Non-retryable: auth_failed, invalid_request, context_length_exceeded

### Fallback Model Chain
- DeepSeek V4 Flash → DeepSeek V4 Pro → Qwen 3.6 Plus
- Qwen 3.5 Plus → Qwen 3.6 Plus
- Qwen 3.6 Plus → No fallback (escalate to human)

---

## 7. Tech Stack

| Thành phần | Tech | Lý do |
|---|---|---|
| **Brain orchestration** | Python, FastAPI | Async, type-safe, AI tooling mạnh |
| **State machine** | Python, FastAPI | Tự build, workflow governance |
| **Backend API** | FastAPI | Nhanh, async, AI tooling mạnh |
| **Database** | PostgreSQL, pgvector | Transaction, audit, vector search |
| **ORM** | SQLAlchemy (async) | Python standard, type-safe |
| **Validation** | Pydantic | FastAPI native, type-safe |
| **Cache/Queue** | Redis | Nhanh, rate limit, job queue |
| **Migrations** | Alembic | Database version control |
| **Auth** | JWT + API Key | Bảo mật API endpoints |
| **LLM Gateway** | LiteLLM + OpenCode | LiteLLM cho simple calls, OpenCode cho coding |
| **Execution (Dev)** | OpenCode tools | bash, edit, write, read — nhanh |
| **Execution (Prod)** | Docker, Ubuntu | Isolated, safe |
| **CI/CD** | GitHub Actions | Phổ biến, dễ tích hợp |
| **Frontend** | Next.js, TailwindCSS, Recharts, Zustand | Modern, reactive |
| **Monitoring** | Prometheus, Loki, Grafana, OpenTelemetry | Full observability |
| **Reverse Proxy** | Nginx | SSL, load balancing |
| **LLMs** | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus | Cost-effective |
| **Embeddings** | Configurable (OpenAI/BGE) | pgvector search |

---

## 8. Cấu trúc thư mục

```
project/
├── governance/
│   └── laws.yaml                    # 20 architectural laws (v3)
├── database/
│   └── schema.sql                   # PostgreSQL schema (15+ tables, v2)
├── docs/
│   ├── ARCHITECTURE.md              # This file (v3)
│   ├── state-machine.md             # Workflow state machine (v2)
│   ├── agent-matrix.md             # Agent responsibility matrix
│   ├── opencode-architecture.md    # OpenCode integration design (v3)
│   ├── security-design.md          # Auth, RBAC, API security
│   ├── error-handling-resilience.md # Circuit breaker, retry, fallback
│   ├── llm-integration.md          # LLM call management (v3)
│   ├── database-migration.md       # Alembic migration strategy
│   ├── api-specification.md        # REST API design
│   ├── testing-strategy.md         # Testing approach
│   ├── non-functional-requirements.md # NFRs
│   ├── mvp-scope.md               # Trimmed MVP definition
│   ├── llm-observability.md        # LLM metrics, cost tracking
│   ├── risk-assessment.md          # Risks and mitigations
│   ├── data-flow.md                # Data flow diagrams (v3)
│   └── architecture-change-log.md  # v2 → v3 change log (NEW)
├── specs/
│   ├── gatekeeper.yaml             # Gatekeeper agent spec
│   ├── orchestrator.yaml           # Orchestrator agent spec
│   ├── specialist.yaml             # Specialist agent spec
│   ├── auditor.yaml                # Auditor agent spec
│   ├── mentor.yaml                 # Mentor agent spec
│   ├── devops.yaml                 # DevOps agent spec
│   ├── monitoring.yaml             # Monitoring agent spec
│   └── opencode_integration.yaml   # OpenCode integration spec (v3, renamed)
├── agents/
│   └── prompts/                    # Prompt templates (7 agents)
│       ├── gatekeeper.txt
│       ├── orchestrator.txt
│       ├── coder.txt
│       ├── reviewer.txt
│       ├── mentor.txt
│       ├── devops.txt
│       └── monitoring.txt
├── shared/
│   └── config/
│       ├── models.yaml              # Model config (env vars, circuit breaker, quota)
│       └── state_transitions.py     # State transition rules (v2: +FAILED, CANCELLED)
├── services/
│   ├── orchestrator/                # FastAPI backend (Phase 1)
│   ├── execution/                   # Execution layer (Phase 1)
│   │   ├── opencode_integration.py  # OpenCode integration (v3)
│   │   └── sandbox_manager.py       # Docker sandbox
│   └── memory/                      # Memory system (Phase 6)
│       ├── ledger.py
│       └── retrieval.py
├── apps/
│   └── dashboard/                   # Next.js frontend (Phase 7)
├── docker-compose.yml
├── pyproject.toml
└── alembic/
```

---

## 9. Execution Mode

### Dev Mode (OpenCode Tools)
- **Tools**: bash, edit, write, read, glob, grep
- **Use case**: Development, prototyping, fast iteration
- **Command allowlist**: pytest, ruff, mypy, npm, git, docker
- **Command blocklist**: rm -rf /, sudo, chmod 777

### Production Mode (Docker Sandbox)
- **Tools**: Docker container, Ubuntu base image
- **Use case**: Production deployment, untrusted code
- **Advantages**: Fully isolated, safe, reproducible

### Mode Selection
- **Auto**: Based on risk level (LOW/MEDIUM → dev, HIGH/CRITICAL → prod)
- **Manual**: User can force via API
- **Default**: Dev mode for development

---

## 10. Quality Checks (7 Steps)

Hệ thống có **7 bước kiểm tra chất lượng** xuyên suốt workflow:

| # | Bước | Khi nào | Ai làm | Model | Fail → |
|---|---|---|---|---|---|
| 1 | **Validation Gate** | Input classification | Gatekeeper + Validator | Flash + Qwen 3.5 | Re-analyze / Mentor |
| 2 | **Gatekeeper Validation** | NEW → ANALYZING | Gatekeeper | DeepSeek V4 Flash | BLOCKED |
| 3 | **Orchestrator Planning** | ANALYZING → PLANNING | Orchestrator | Qwen 3.6 Plus | BLOCKED |
| 4 | **Verification Sandbox** | IMPLEMENTING → VERIFYING | System (auto) | — | IMPLEMENTING (retry) |
| 5 | **Auditor Review** | VERIFYING → REVIEWING → DONE | Auditor | Qwen 3.5 Plus | IMPLEMENTING / ESCALATED |
| 6 | **Mentor Escalation** | ESCALATED → PLANNING/FAILED | Mentor | Qwen 3.6 Plus | FAILED / PLANNING |
| 7 | **Audit Trail** | Mọi state transition | System | — | Log + alert |

### 1. Validation Gate (NEW — Dual-Model Cross-Validation)

```
User request → Gatekeeper (DeepSeek V4 Flash) → Classification
                    ↓
              Validator (Qwen 3.5 Plus) → Cross-validate
                    ↓
              APPROVED (≥0.8) → Pass to Orchestrator
              APPROVED (<0.8) → Gatekeeper re-analyze
              REJECTED        → Escalate to Mentor
```

**Khi nào skip**: Risk = LOW AND Complexity = TRIVIAL/SIMPLE

## 11. Confidence Calculation

```
Confidence = clamp(T × 0.35 + L × 0.15 - P × 0.20 + A × 0.30, 0, 1)

Where:
  T = test pass rate (0-1)
  L = lint/code quality score (0-1)
  P = retry penalty (0-1, higher = more retries)
  A = architectural law compliance (0-1)

The result is clamped to [0, 1] to prevent negative values.
```

---

## 12. Phases triển khai

| Phase | Tên | Thời gian | Mục tiêu | Trạng thái |
|---|---|---|---|---|
| 0 | System Design | 1-2 tuần | Luật, state machine, schema, docs | ✅ Complete (v4) |
| 1 | Core State System | 2-3 tuần | Project/Module/Task Registry, State Engine, Auth | 🟡 60% |
| 2 | Workflow Engine | 2-3 tuần | FastAPI orchestration, agent dispatch, escalation | ⬜ Pending |
| 3 | Agent Runtime | 2-4 tuần | 7 agents, LLM Gateway, model routing, prompts | ⬜ Pending |
| 4 | Verification Sandbox | 2-3 tuần | OpenCode dev mode + Docker prod mode | ⬜ Pending |
| 5 | Governance Layer | 2 tuần | Confidence, laws, cost, risk | ⬜ Pending |
| 6 | Memory System | 2-3 tuần | Instruction ledger, semantic retrieval | ⬜ Pending |
| 7 | Dashboard & Observability | 2-3 tuần | Next.js dashboard, Prometheus, Grafana | ⬜ Pending |
| 8 | Deployment & Operations | 2-3 tuần | Staging/production deploy, rollback | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | Multi-project, self-improving | ⬜ Pending |

### MVP (8-11 weeks)
Phases 0-4 only — prove the core workflow works end-to-end. See `docs/mvp-scope.md` for details.

---

## 12.5 Risk Mitigations (v4.1)

### Risk #1: State Bloat & Race Conditions — MITIGATED
- **Optimistic locking**: `version` column on tasks table + `SELECT FOR UPDATE`
- **Retry on conflict**: `@retry_on_conflict` decorator with exponential backoff
- **Stuck task detection**: Background job every 5 minutes
- **Auto-escalation**: Tasks stuck >60min → ESCALATED, BLOCKED >120min → ESCALATED
- **Risk score reduced**: 12 → 8 (HIGH)

### Risk #2: Context Window / "Lost in the Middle" — MITIGATED
- **ContextBuilder**: Priority-based truncation (P100 → P10)
- **"Lost in the Middle" mitigation**: Critical info at BEGINNING and END
- **Token counting**: Pre-send validation against model limits
- **Overflow protocol**: Escalate, model upgrade, context reduction
- **Risk score reduced**: 6 → 4 (MEDIUM)

### Risk #3: Dependency Blocked — MITIGATED
- **BLOCKED timeout**: 120 minutes → auto-escalate to ESCALATED
- **Human-in-the-loop**: Auto-notification via Dashboard, Slack, Email
- **Warning system**: 60-minute warning before escalation
- **New transition**: BLOCKED → ESCALATED (was only PLANNING, CANCELLED)
- **New table**: `notifications` for audit and retry
- **Risk score**: 9 (HIGH) — new risk, fully mitigated

---

## 13. Key Changes from v2 to v3

| Change | v2 | v3 |
|---|---|---|
| Brain | OpenCode | **FastAPI backend** |
| OpenCode role | Central brain | **LLM + Tool provider** |
| LLM calls | All via OpenCode | **LiteLLM (simple) + OpenCode (coding)** |
| State machine | OpenCode quản lý | **FastAPI engine** |
| Agent dispatch | OpenCode calls agents | **FastAPI router dispatch** |
| Cost tracking | OpenCode tính | **FastAPI cost tracker** |
| Audit logging | OpenCode log | **FastAPI audit middleware** |
| State machine | 9 states | 11 states (+FAILED, +CANCELLED) |
| Terminal states | 1 (DONE) | 3 (DONE, FAILED, CANCELLED) |
| ESCALATED→DONE | Allowed | Only with verified output evidence |
| Dependencies | UUID[] array | Junction tables |
| Embedding dim | Hardcoded 1536 | Configurable via embedding_config |
| Auth | None | JWT + API Key |
| LLM endpoints | Hardcoded | Environment variables |
| Circuit breaker | None | Per-model circuit breaker |
| Mentor quota | yaml config only | Database-enforced |
| Confidence | Could go negative | Clamped to [0, 1] |
| Cost tracking | Basic | Detailed per-call logging |
| LLM observability | None | metrics, latency, success rate per agent |
| Laws | 12 | 20 (added auth, circuit breaker, terminal states, etc.) |
| Prompt templates | 4 | 7 (added orchestrator, devops, monitoring) |
| Design docs | 4 | 15+ (added security, resilience, LLM, api, etc.) |

---

## 14. Metadata
- **Version**: 5.0.0
- **Created**: 2026-05-14
- **Last Updated**: 2026-05-16
- **Status**: Phase 0 ✅ | Phase 1 ✅ | Phase 2 ✅
- **Phase 1**: 115 tests pass (79% coverage), 48+ files, CRUD APIs, Validation Gate, Risk Mitigations
- **Phase 2**: 202 tests pass, 65+ files, Workflow Engine, LLM Gateway, Agent Dispatcher, Prompt Templates
- **v5.0.0 Change**: Phase 2 Workflow Engine complete:
  - LLM Gateway (circuit breaker + retry + fallback + cost tracking + rate limiting)
  - Agent Dispatcher (7 agents, state-based routing, prompt templates)
  - Workflow Engine (state machine nodes, audit logging, cancellation)
  - Workflow API (execute, status, cancel, retry endpoints)
  - 87 new tests (202 total)
