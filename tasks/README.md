# AI SDLC SYSTEM — PROJECT TASKS INDEX

## Hệ Thống Điều Phối AI SDLC
### AI Software Company Operating System

---

## Cấu trúc thư mục

```
tasks/
├── README.md                              # File này — Index tổng hợp
├── phase-0-system-design.md               # Phase 0: System Design ✅ COMPLETE
├── phase-1-core-state-system.md           # Phase 1: Core State System
├── phase-2-workflow-engine.md             # Phase 2: Workflow Engine
├── phase-3-agent-runtime.md               # Phase 3: Agent Runtime
├── phase-4-verification-sandbox.md        # Phase 4: Verification Sandbox (Hybrid)
├── phase-5-governance-layer.md            # Phase 5: Governance Layer
├── phase-6-memory-system.md               # Phase 6: Memory System
├── phase-7-dashboard-observability.md     # Phase 7: Dashboard & Observability
├── phase-8-deployment-operations.md       # Phase 8: Deployment & Operations
└── phase-9-optimization-autonomy.md       # Phase 9: Optimization & Autonomy
```

---

## Tổng quan các phases

| Phase | Tên | Thời gian | Số tasks | Trạng thái |
|---|---|---|---|---|---|
| 0 | System Design | 1–2 tuần | 31 | ✅ 100% |
| 1 | Core State System | 2–3 tuần | 48 | ✅ 100% |
| 2 | Workflow Engine | 2–3 tuần | 42 | ✅ 100% |
| 3 | Agent Runtime | 2–4 tuần | 55 | ✅ 100% |
| 4 | Verification Sandbox (Hybrid) | 2–3 tuần | 51 | ✅ 100% |
| 5 | Governance Layer | 2 tuần | 28 | ⬜ Pending |
| 6 | Memory System | 2–3 tuần | 28 | ⬜ Pending |
| 7 | Dashboard & Observability | 2–3 tuần | 32 | ⬜ Pending |
| 8 | Deployment & Operations | 2–3 tuần | 32 | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | 25 | ⬜ Pending |

**Tổng cộng: ~358 tasks — 215 tests passing**

---

## Hybrid Architecture (v4)

```
FastAPI Backend (BRAINS)
├── State Machine Engine (22 valid transitions)
├── Workflow Engine
├── Dynamic Model Router (v4 — auto-select model by scoring)
├── Agent Router & Dispatcher
├── LLM Gateway (LiteLLM + OpenCode)
│   ├── Circuit Breaker (per-model)
│   ├── Retry w/ Backoff
│   └── Cost Tracker
└── Audit Middleware
        │
        ▼
Execution Layer (Hybrid)
├── Dev Mode → OpenCode tools (bash, edit, write, read, glob, grep)
└── Prod Mode → Docker sandbox (isolated container)
```

### Dynamic Model Router (v4)
- **5 Models**: DeepSeek V4 Flash, DeepSeek V4 Pro, Qwen 3.5 Plus, Qwen 3.6 Plus, MiniMax M2.7
- **Scoring**: capability_match (40%) + context_fit (20%) + speed (15%) + cost (15%) + circuit_breaker (10%)
- **Self-Awareness Prompts**: Each model receives role, strengths, limitations, handoff protocol
- **Fallback Chains**: Auto-fallback + escalate to Mentor if all fail

### Mode Selection
| Risk Level | Execution Mode | Lý do |
|---|---|---|
| LOW | Dev (OpenCode) | Nhanh, trusted code |
| MEDIUM | Dev (OpenCode) | Fast iteration |
| HIGH | Prod (Docker) | Isolated execution |
| CRITICAL | Prod (Docker) | Maximum safety |

---

## Thứ tự ưu tiên thực tế

```
State → Workflow → Execution → Verification → Governance → Memory → Dashboard → Deployment → Optimization
  ↓         ↓           ↓            ↓              ↓           ↓          ↓           ↓           ↓
Phase 0   Phase 2     Phase 3      Phase 4        Phase 5     Phase 6    Phase 7     Phase 8     Phase 9
Phase 1
```

---

## Tech Stack tổng quan

| Thành phần | Tech | Ghi chú |
|---|---|---|
| Core orchestration | Python, State Machine | Tự build, không dùng LangGraph |
| Execution (Dev) | OpenCode tools | bash, edit, write, read, glob, grep |
| Execution (Prod) | Docker, Ubuntu | Isolated container |
| Backend API | FastAPI | Nhanh, async |
| Database | PostgreSQL, pgvector | Transaction + vector search |
| ORM | SQLAlchemy | Type-safe |
| Validation | Pydantic | FastAPI native |
| Cache/Queue | Redis | Fast, rate limit |
| CI/CD | GitHub Actions | Automated pipeline |
| Frontend | Next.js, TailwindCSS, Recharts, Zustand | Modern dashboard |
| Monitoring | Prometheus, Loki, Grafana, OpenTelemetry | Full observability |
| Reverse Proxy | Nginx | SSL, load balancing |
| Cloud | AWS / Hetzner / GCP | Flexible deployment |
| LLMs | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus | Cost-effective |
| Embeddings | OpenAI text-embedding-3-small / BGE | Semantic search |

---

## Links đến từng phase

- [✅ Phase 0: System Design](./phase-0-system-design.md) — **COMPLETE (v4)**
- [✅ Phase 1: Core State System](./phase-1-core-state-system.md) — **100% COMPLETE**
- [✅ Phase 2: Workflow Engine](./phase-2-workflow-engine.md) — **100% COMPLETE**
- [✅ Phase 3: Agent Runtime](./phase-3-agent-runtime.md) — **100% COMPLETE**
- [✅ Phase 4: Verification Sandbox (Hybrid)](./phase-4-verification-sandbox.md) — **100% COMPLETE**
- [Phase 5: Governance Layer](./phase-5-governance-layer.md)
- [Phase 6: Memory System](./phase-6-memory-system.md)
- [Phase 7: Dashboard & Observability](./phase-7-dashboard-observability.md)
- [Phase 8: Deployment & Operations](./phase-8-deployment-operations.md)
- [Phase 9: Optimization & Autonomy](./phase-9-optimization-autonomy.md)

---

## Project Progress (Updated 2026-05-16)

### ✅ Đã hoàn thành qua các Phase
| Component | Phase | Mô tả |
|---|---|---|
| **Config + DB** | 1 | Settings, async DB engine, Redis cache, Alembic |
| **ORM Models** | 1 | 19 SQLAlchemy models (user, project, module, task, registry) |
| **Pydantic Schemas** | 1 | CRUD DTOs cho project, module, task, retry, audit, verification |
| **Services** | 1 | CRUD business logic, state transitions, retry, audit |
| **REST API** | 1 | 20+ endpoints (projects, modules, tasks, audit, retry) |
| **Middleware** | 1 | HTTP request audit logging |
| **Unit Tests** | 1 | 38 tests (schemas, services, state transitions) |
| **Workflow Engine** | 2 | 8 node types, state machine loop, error handling, timeout |
| **Dependency Mgmt** | 2 | DependencyGraph, circular detection, auto-unblock |
| **Retry & Escalation** | 2 | Auto-escalate, mentor takeover |
| **Model Router** | 3 | Scoring-based (5 models), fallback, circuit breaker |
| **Agent Runtime** | 3 | execute, retry, escalate, takeover, cost tracking |
| **Prompt Templates** | 3 | 10 templates + renderer + versioning |
| **OpenCode Adapter** | 3 | bash, read, write, edit file operations |
| **Specialist Agent** | 3 | Code generation + module design |
| **Auditor Agent** | 3 | 5 audit checks + verdict (APPROVED/REVISE/ESCALATE) |
| **Mentor Agent** | 3 | Deadlock resolution + final verdict |
| **DevOps Agent** | 3 | Build + deploy |
| **Monitoring Agent** | 3 | Error tracking + anomaly detection |
| **Verification Pipeline** | 4 | 5 steps (lint, test, integration, build, security) |
| **Dev Mode** | 4 | OpenCode bash delegation |
| **Docker Prod Mode** | 4 | --network none --read-only --cpus 2 --memory 4g |
| **Rollback Engine** | 4 | Git revert + audit log |
| **Mode Selector** | 4 | Risk-based dev/prod routing |
| **CI/CD** | 4 | GitHub Actions + trigger/callback/status |
| **Integration Tests** | 1-4 | 191 tests passing |

### ⬜ Còn lại
| Component | Phase | Ghi chú |
|---|---|---|
| **Memory System** | 6 | Chưa bắt đầu |
| **Governance Layer** | 5 | Chưa bắt đầu |
| **Dashboard** | 7 | Chưa bắt đầu |
| **Deployment** | 8 | Chưa bắt đầu |
| **DB Migration** | 1 | Run alembic upgrade head (chờ môi trường có pip) |
