# ARCHITECTURE - AI SDLC Orchestrator

## AI Software Company Operating System

---

## 1. Tổng quan

Hệ thống điều phối AI SDLC mô phỏng một công ty phần mềm dùng AI, trong đó người dùng chỉ cần mô tả nghiệp vụ, mục tiêu hoặc yêu cầu sản phẩm. Phần còn lại hệ thống tự động thực hiện theo quy trình chuẩn của một đội ngũ kỹ thuật chuyên nghiệp.

### Mục tiêu
- Tiếp nhận yêu cầu → Phân tích → Thiết kế → Chia task → Triển khai → Kiểm tra → Deploy → Giám sát → Bảo trì
- Không phải một AI làm mọi thứ mơ hồ, mà là hệ thống có quy trình, phân vai, luật lệ, kiểm chứng và khả năng học

### Nguyên lý cốt lõi
1. **FastAPI là bộ não** — Điều phối toàn bộ: state machine, workflow engine, agent dispatch, cost tracking, audit logging
2. **LLM Gateway** — OpenCodecho simple calls,OpenCode integration cho coding tasks
3. **Dynamic Model Router** — Chọn model dựa trên TaskProfile (complexity, risk, domain)
4. **Workflow theo trạng thái** — Mọi task đi qua các trạng thái rõ ràng (11 states, 3 terminal)
5. **Có lớp quản trị** — Mọi output đều qua luật (20 laws), ngưỡng tin cậy, kiểm tra
6. **Có bộ nhớ ngoài** — AI đọc trạng thái từ database, pgvector cho semantic search
7. **Có cơ chế kiểm chứng** — 5-step pipeline: lint → test → build → security scan
8. **Có fallback và resilience** — Circuit breaker, retry với backoff, fallback model, rollback engine

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
│  │State Machine│  │Workflow     │  │   Dynamic Model Router  │ │
│  │  Engine     │  │  Engine     │  │   & Agent Dispatcher    │ │
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
│  │              Agent Runtime (10 agents)                      │  │
│  │  Gatekeeper | Orchestrator | Validator | Specialist      │  │
│  │  Auditor | Mentor | DevOps | Monitoring                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Verification Pipeline (5 steps)                │  │
│  │  Lint → Unit Test → Integration Test → Build → Security  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Execution Layer                                │  │
│  │  Dev Mode:OpenCode tools (bash, edit, write, read)      │  │
│  │  Prod Mode: Docker sandbox (isolated)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │  PostgreSQL  │  │    Redis     │  │   LLM APIs    │
   │ (20 tables, │  │  (Cache,    │  │ (via OpenCode│
   │  pgvector)  │  │  Rate Limit)│  │  orOpenCode) │
   └──────────────┘  └──────────────┘  └──────────────┘
```

### Execution Flow

```
1. User → FastAPI receives request (POST /api/v1/tasks)
2. FastAPI → Gatekeeper agent (via LLM Gateway → OpenCode)
3. FastAPI → Validator agent (cross-validate classification)
4. FastAPI → Orchestrator agent (via LLM Gateway → OpenCode)
5. FastAPI → State Machine (validate transition, update DB)
6. FastAPI → Specialist agent (via LLM Gateway →OpenCode for code + tools)
7. FastAPI → Verification Pipeline (5-step: lint/test/build/security)
8. FastAPI → Confidence Engine (TLPA formula)
9. FastAPI → Auditor agent (5-dimension review)
10. FastAPI → Law Engine (20 laws compliance check)
11. FastAPI → State Machine (update status in DB)
12. FastAPI → Memory (store lesson learned in PostgreSQL)
```

---

## 3. 6 Lớp chính

### 3.1. FastAPI Brain Layer
- **State machine engine**: Validate và thực thi 22 state transitions
- **Workflow engine**: Điều phối task lifecycle từ NEW → DONE
- **Agent router**: Dispatch agents dựa trên task type và complexity
- **LLM Gateway**: Dynamic Model Router, Circuit breaker, retry, fallback, cost tracking
- **Audit logging**: Log mọi action với actor, timestamp, result + WebSocket broadcast

### 3.2. State Machine Layer
- **11 states**: NEW, ANALYZING, PLANNING, IMPLEMENTING, VERIFYING, REVIEWING, DONE, ESCALATED, BLOCKED, FAILED, CANCELLED
- **22 valid transitions** với điều kiện
- **3 terminal states**: DONE, FAILED, CANCELLED
- **State validation**: Mọi transition được validate trước khi thực thi
- **Optimistic locking**: Prevents concurrent state transition conflicts

### 3.3. Governance Layer
- **20 architectural laws** enforcement (regex-based pattern detection)
- **Confidence scoring**: TLPA formula (Test 0.35 + Lint 0.15 - Penalty 0.20 + Law 0.30)
- **Cost governor**: Giới hạn token usage, mentor calls
- **Risk classification**: 4-axis scoring (complexity, data sensitivity, user impact, deployment scope)
- **Mentor quota**: 10 calls/day, enforced via database

### 3.4. Verification Layer (5-Step Pipeline)
| Step | Tool (Python/Node) | Weight | Critical? |
|------|-------------------|--------|-----------|
| Lint | ruff/flake8 hoặc eslint/tsc | 15 | ❌ |
| Unit Test | pytest hoặc npm test | 40 | ✅ |
| Integration Test | pytest integration | 25 | ✅ |
| Build | python build hoặc npm run build | 10 | ✅ |
| Security Scan | bandit hoặc npm audit | 10 | ✅ |

- **Score threshold**: 60/100 → pass
- **Fail-fast**: Dừng ngay nếu critical step fail
- **Max retries**: 2 lần
- **Dev mode**:OpenCode bash tool
- **Prod mode**: Docker container isolated

### 3.5. Memory Layer (Phase 6)
- **Instruction ledger**: Lưu mentor advice, warnings, decisions, patterns
- **Semantic retrieval**: Pseudo-embeddings + cosine similarity, configurable dimensions
- **Decision history**: Lưu quyết định kiến trúc, lý do, alternatives
- **Memory caching**: Redis + in-memory fallback với TTL

### 3.6. Observability Layer (Phase 7)
- **OpenTelemetry tracing**: Distributed tracing cho mọi request
- **Prometheus metrics**: Task counts, cost, latency, retry rate, confidence
- **JSON structured logging**: Mọi log event dưới dạng JSON
- **Grafana dashboards**: Real-time monitoring với auto-provisioning
- **Alert rules**: 5 rules (failure rate, quota, retry, confidence, cost)

---

## 4. Workflow State Machine

```
NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
  │       │          │            │             │            │
  │       │          │            │             │            └─ Auditor approve (≥0.80)
  │       │          │            │             └─ 5-step pipeline (score ≥60)
  │       │          │            └─ Code hoàn thành
  │       │          └─ Agent nhận task
  │       └─ Orchestrator chia task
  └─ Gatekeeper phân loại

Terminal states:
  DONE       — Task hoàn thành thành công
  FAILED     — Task thất bại vĩnh viễn (Mentor reject, fatal error)
  CANCELLED  — Task hủy bởi user

Special states:
  ESCALATED  — Mentor takeover khi retry > 2 hoặc confidence < 0.30
  BLOCKED    — Chờ đợi dependency
```

---

## 5. Agent Architecture

### FastAPI as the Brain
FastAPI điều phối toàn bộ agent lifecycle:
1. **Prompt loading**: Load template từ `/agents/prompts/*.txt`
2. **Context building**: Assemble task context (spec, modules, memory, laws)
3. **LLM call**: Through LLM Gateway (Dynamic Model Router + circuit breaker + cost tracking)
   - Path 1:OpenCode (Gatekeeper, Orchestrator, Validator, Mentor, Monitoring)
   - Path 2:OpenCode integration (Specialist, Auditor, DevOps)
4. **Result parsing**: Parse JSON output từ agent
5. **Tool execution**: Execute code changes viaOpenCode tools
6. **State transition**: Update task status trong state machine

### 10 Agents (Prompt Templates)

| Agent | Vai trò | Model Preference | LLM Path |OpenCode Tools |
|---|---|---|---|---|
| **Gatekeeper** | Phân loại, routing | DeepSeek V4 Flash | OpenCode| — |
| **Orchestrator** | Điều phối, chia task | Qwen 3.6 Plus | OpenCode| — |
| **Validator** | Cross-validate Gatekeeper | Qwen 3.5 Plus | OpenCode| — |
| **Specialist** | Viết code, thực thi | DeepSeek V4 Pro |OpenCode | bash, edit, write, read, glob, grep |
| **Auditor** | Review 5 dimensions | Qwen 3.5 Plus | OpenCode| read, glob, grep |
| **Mentor** | Quyết định chiến lược | Qwen 3.6 Plus | OpenCode| — |
| **DevOps** | Build, deploy, rollback | DeepSeek V4 Pro |OpenCode | bash, read |
| **Monitoring** | Giám sát, alert | DeepSeek V4 Flash | OpenCode| — |

> **Note:** `coder.txt` = `specialist.txt` (duplicate), `reviewer.txt` = `auditor.txt` (duplicate).

### Tool Restrictions per Agent
- **Specialist**: Full access (bash, edit, write, read, glob, grep) — cần viết code
- **Auditor**: Read-only + bash (chỉ chạy tests) — không sửa code
- **Gatekeeper/Orchestrator/Validator/Mentor/Monitoring**: Không cần tools — chỉ phân tích, điều phối
- **DevOps**: bash + read — build và deploy

---

## 6. Resilience & Error Handling

### Circuit Breaker
- Mỗi LLM model có circuit breaker riêng
- **Closed**: Bình thường, gọi API
- **Open**: 5 lỗi liên tiếp → chuyển sang fallback model, chờ 60s
- **Half-Open**: Thử 3 calls, nếu thành công → Closed lại

### Retry with Exponential Backoff
- Max 3 retries cho LLM API calls
- Backoff: 1s → 2s → 4s (+ jitter)
- Retryable: timeout, rate_limit, server_error
- Non-retryable: auth_failed, invalid_request, context_length_exceeded

### Fallback Model Chain
- DeepSeek V4 Flash → DeepSeek V4 Pro → Qwen 3.6 Plus
- Qwen 3.5 Plus → Qwen 3.6 Plus
- Qwen 3.6 Plus → No fallback (escalate to human)

### Rollback Engine
- **Git revert**: Tự động revert commit khi verification fail
- **Snapshot restore**: pg_restore từ backup
- **Auto-rollback**: Configurable, max 3 rollbacks

---

## 7. Tech Stack

| Thành phần | Tech | Lý do |
|---|---|---|
| **Brain orchestration** | Python, FastAPI | Async, type-safe, AI tooling mạnh |
| **State machine** | Python, FastAPI | Tự build, workflow governance |
| **Backend API** | FastAPI | Nhanh, async, AI tooling mạnh |
| **Database** | PostgreSQL 16, pgvector | Transaction, audit, vector search |
| **ORM** | SQLAlchemy 2.0 (async) | Python standard, type-safe |
| **Validation** | Pydantic | FastAPI native, type-safe |
| **Cache/Queue** | Redis 7 | Nhanh, rate limit, job queue |
| **Migrations** | Alembic | Database version control |
| **Auth** | JWT + API Key | Bảo mật API endpoints |
| **LLM Gateway** |OpenCode |OpenCode cho tất cả LLM calls |
| **Execution (Dev)** |OpenCode tools | bash, edit, write, read — nhanh |
| **Execution (Prod)** | Docker, Ubuntu | Isolated, safe |
| **CI/CD** | GitHub Actions | Phổ biến, dễ tích hợp |
| **Frontend** | Next.js 14, TailwindCSS 3, shadcn/ui, Recharts, Zustand, Framer Motion | Modern, reactive |
| **Monitoring** | Prometheus, Loki, Promtail, Grafana, OpenTelemetry | Full observability |
| **LLMs** | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus | Cost-effective |
| **Embeddings** | Configurable (OpenAI/BGE) | pgvector search |

---

## 8. Cấu trúc thư mục

Xem [README.md](./README.md) — Cấu trúc thư mục đầy đủ.

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

## 10. Confidence Calculation

```
Confidence = clamp(T × 0.35 + L × 0.15 - P × 0.20 + A × 0.30, 0, 1)

Where:
  T = test pass rate (0-1)
  L = lint/code quality score (0-1)
  P = retry penalty (0-1, higher = more retries)
  A = architectural law compliance (0-1)

Thresholds:
  ≥ 0.80 → Auto-approve → DONE
  0.60-0.79 → Require review → REVIEWING
  0.30-0.59 → Escalate → Mentor
  < 0.30 → Takeover & rollback
```

---

## 11. Phases triển khai

| Phase | Tên | Thời gian | Mục tiêu | Trạng thái |
|---|---|---|---|---|
| 0 | System Design | 1-2 tuần | Luật, state machine, schema, docs | ✅ Complete (v4) |
| 1 | Core State System | 2-3 tuần | CRUD APIs, ORM, Alembic, Redis | ✅ Complete |
| 2 | Workflow Engine | 2-3 tuần | State machine, node execution, retries | ✅ Complete |
| 3 | Agent Runtime | 2-4 tuần | 10 agents, LLM Gateway, model routing | ✅ Complete |
| 4 | Verification Sandbox | 2-3 tuần | 5-step pipeline, dev/prod modes | ✅ Complete |
| 5 | Governance Layer | 2 tuần | Confidence, laws, risk, cost | ✅ Complete |
| 6 | Memory System | 2-3 tuần | Ledger, semantic search, decisions | ✅ Complete |
| 7 | Dashboard & Observability | 2-3 tuần | Next.js + shadcn/ui, Prometheus, Grafana | ✅ Complete |
| 8 | Deployment & Operations | 2-3 tuần | Staging/production deploy, rollback | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | Multi-project, self-improving | ⬜ Pending |

---

## 12. Key Changes from v2 to v5

| Change | v2 | v3-v4 | v5 (Current) |
|---|---|---|---|
| Brain |OpenCode | **FastAPI backend** | FastAPI backend |
|OpenCode role | Central brain | **LLM + Tool provider** | LLM + Tool provider |
| LLM calls | All viaOpenCode | **OpenCode** |OpenCode |
| Model routing | Fixed | Fixed | **Dynamic Model Router** |
| State machine | 9 states | 11 states | 11 states |
| Terminal states | 1 (DONE) | 3 (DONE, FAILED, CANCELLED) | 3 |
| Dependencies | UUID[] array | Junction tables | Junction tables |
| Auth | None | JWT + API Key | JWT + API Key |
| Circuit breaker | None | Per-model | Per-model |
| Mentor quota | yaml config only | Database-enforced | Database-enforced |
| Confidence | Could go negative | Clamped [0, 1] | Clamped [0, 1] |
| Cost tracking | Basic | Per-call logging | Per-call logging |
| Laws | 12 | 20 | 20 |
| Prompt templates | 4 | 7 | **10** (+ validator, duplicates) |
| Design docs | 4 | 15+ | 16 |
| Memory | — | — | **Phase 6: ledger, embedding, decision** |
| Dashboard | — | — | **Phase 7: Next.js + shadcn/ui** |
| Observability | — | — | **Phase 7: OpenTelemetry, Prometheus, Grafana** |
| Tests | — | 38 | **478** |

---

## 13. Metadata
- **Version**: 5.0.0
- **Created**: 2026-05-14
- **Last Updated**: 2026-05-17
- **Status**: Phases 0-7 Complete, Phase 8 Pending
- **Tests**: 478/478 pass
