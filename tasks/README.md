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
|---|---|---|---|---|
| 0 | System Design | 1–2 tuần | 31 | ✅ Complete (v4.1) |
| 1 | Core State System | 2–3 tuần | 56 | 🟡 Partial (65%) |
| 2 | Workflow Engine | 2–3 tuần | 42 | ⬜ Pending |
| 3 | Agent Runtime | 2–4 tuần | 55 | ⬜ Pending |
| 4 | Verification Sandbox (Hybrid) | 2–3 tuần | 35 | ⬜ Pending |
| 5 | Governance Layer | 2 tuần | 28 | ⬜ Pending |
| 6 | Memory System | 2–3 tuần | 28 | ⬜ Pending |
| 7 | Dashboard & Observability | 2–3 tuần | 32 | ⬜ Pending |
| 8 | Deployment & Operations | 2–3 tuần | 32 | ⬜ Pending |
| 9 | Optimization & Autonomy | Liên tục | 25 | ⬜ Pending |

**Tổng cộng: ~366 tasks** (8 new tasks added in v4.1: validation gate)

---

## Hybrid Architecture (v4.1)

```
FastAPI Backend (BRAINS)
├── State Machine Engine (22 valid transitions, v3 gatecheck)
├── Workflow Engine
├── Dual-Model Validation Gate (v4.1 — cross-validate before NEW → ANALYZING)
├── Dynamic Model Router (v4 — auto-select model by scoring)
├── Agent Router & Dispatcher (8 agents: 7 + Validator)
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

### Dual-Model Validation Gate (v4.1)
- **Gatekeeper** (DeepSeek V4 Flash): Classifies task
- **Validator** (Qwen 3.5 Plus): Cross-validates classification
- **Decision**: APPROVED ≥0.8 → pass | <0.8 → reanalyze | REJECTED → escalate
- **Skip**: Risk=LOW AND Complexity=TRIVIAL/SIMPLE

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
- [🟡 Phase 1: Core State System](./phase-1-core-state-system.md) — **65% COMPLETE**
- [Phase 2: Workflow Engine](./phase-2-workflow-engine.md)
- [Phase 3: Agent Runtime](./phase-3-agent-runtime.md)
- [Phase 4: Verification Sandbox (Hybrid)](./phase-4-verification-sandbox.md)
- [Phase 5: Governance Layer](./phase-5-governance-layer.md)
- [Phase 6: Memory System](./phase-6-memory-system.md)
- [Phase 7: Dashboard & Observability](./phase-7-dashboard-observability.md)
- [Phase 8: Deployment & Operations](./phase-8-deployment-operations.md)
- [Phase 9: Optimization & Autonomy](./phase-9-optimization-autonomy.md)

---

## Phase 1 Progress Detail (Updated 2026-05-15)

### ✅ Đã hoàn thành
| Component | Files | Mô tả |
|---|---|---|
| **Config** | settings.py, database.py, cache.py | Settings, async DB engine, Redis cache |
| **ORM Models** | base.py, user.py, project.py, module.py, task.py, registry.py | 15+ SQLAlchemy models |
| **Pydantic Schemas** | project.py, module.py, task.py, validation.py | CRUD DTOs, validation gate DTOs |
| **Services** | projects.py, modules.py, tasks.py, validation.py | CRUD + dual-model validation |
| **Routers** | projects.py, modules.py, tasks.py, validation.py | REST API + validation endpoints |
| **Middleware** | audit.py | HTTP request audit logging |
| **State Machine** | state_transitions.py v3 | 22 transitions + validation gatecheck |
| **Alembic** | alembic.ini, env.py, script.py.mako | Migration framework |
| **Tests** | 4 test files, 38 tests | Unit tests for schemas, services, state |
| **Docs** | dynamic-model-router.md v4.1 | Validation routing + decision matrix |

### ⬜ Chưa hoàn thành
| Component | Missing | Priority |
|---|---|---|
| **Retry Tracking** | Service, APIs, schemas, tests | HIGH |
| **Audit Service** | Service layer, query APIs, CSV export | MEDIUM |
| **Transition Hooks** | Pre/post hooks, dependency checks | MEDIUM |
| **Integration Tests** | End-to-end workflow tests | HIGH |
| **DB Migration** | Run alembic upgrade head | HIGH (blocked by pip) |
| **Validation Tests** | Unit tests for validation service | MEDIUM |
