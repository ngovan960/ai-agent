# Data Flow

## AI SDLC Orchestrator — Data Flow Diagrams

---

## 1. Request Flow (End-to-End)

```
User Request
    │
    ▼ (POST /api/v1/tasks)
┌─────────────────────────────────┐
│  FastAPI Backend                 │
│  ┌───────────────────────────┐  │
│  │  Audit Middleware          │  │ ← Logs every request
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Gatekeeper Agent          │  │ ← Parse, classify complexity
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Validator Agent           │  │ ← Cross-validate classification
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Orchestrator Agent        │  │ ← Break down into tasks
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  State Machine             │  │ ← Validate transition, update DB
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Specialist Agent          │  │ ← Implement code (OpenCode tools)
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Verification Pipeline     │  │ ← 5-step: lint/test/build/security
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Confidence Engine         │  │ ← TLPA formula
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Auditor Agent             │  │ ← 5-dimension review
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Law Engine                │  │ ← 20 laws compliance check
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  State Machine             │  │ ← Update status (DONE/ESCALATED/FAILED)
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Memory System             │  │ ← Store lesson learned
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## 2. Database Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  SQLAlchemy  │────▶│  PostgreSQL  │────▶│  pgvector    │
│  ORM Models  │     │  (20 tables) │     │  (embeddings)│
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  Pydantic    │────▶│  FastAPI     │
│  Schemas     │     │  Responses   │
└──────────────┘     └──────────────┘
```

### Table Relationships

```
users ──┬── projects ──┬── modules ──┬── module_dependencies
        │              │
        │              └── tasks ──┬── task_dependencies
        │                          ├── task_outputs
        │                          ├── retries
        │                          ├── audit_logs
        │                          ├── mentor_instructions
        │                          ├── decisions
        │                          ├── deployments
        │                          ├── cost_tracking
        │                          ├── llm_call_logs
        │                          └── law_violations
        │
        └── api_keys
```

---

## 3. LLM Call Flow

```
Agent Request
    │
    ▼
┌─────────────────────────────────┐
│  LLM Gateway                     │
│  ┌───────────────────────────┐  │
│  │  Dynamic Model Router      │  │ ← Select model based on TaskProfile
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Circuit Breaker           │  │ ← Check if model available
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Retry Handler             │  │ ← Exponential backoff on failure
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  OpenCode / OpenCode        │  │ ← Actual LLM call
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Cost Tracker              │  │ ← Log tokens, cost, latency
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## 4. Verification Pipeline Flow

```
Code Output
    │
    ▼
┌─────────────────────────────────┐
│  Mode Selector                   │ ← Risk-based: dev or prod
│  LOW/MEDIUM → dev               │
│  HIGH/CRITICAL → prod           │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 1: Lint (weight 15)       │ ← ruff/flake8 or eslint/tsc
│  Non-critical, 120s timeout     │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 2: Unit Test (weight 40)  │ ← pytest or npm test
│  Critical, 300s timeout         │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 3: Integration Test (25)  │ ← pytest integration
│  Critical, 300s timeout         │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 4: Build (weight 10)      │ ← python build or npm run build
│  Critical, 120s timeout         │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 5: Security Scan (10)     │ ← bandit or npm audit
│  Critical, 120s timeout         │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Score = (passed_weight/total)  │
│  × 100                          │
│  ≥ 60 → verified                │
│  < 60 → failed                  │
└─────────────────────────────────┘
```

---

## 5. Memory System Flow

```
Task Completion
    │
    ▼
┌─────────────────────────────────┐
│  Memory Integration              │
│  ┌───────────────────────────┐  │
│  │  Instruction Ledger        │  │ ← Store advice, warnings, patterns
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Embedding Engine          │  │ ← Generate pseudo-embeddings
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Decision History          │  │ ← Store decisions with alternatives
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Cache (Redis + in-memory) │  │ ← TTL-based caching
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼ (on next task)
┌─────────────────────────────────┐
│  Semantic Search                 │ ← Cosine similarity retrieval
│  Query → Embedding → Top-K      │
└─────────────────────────────────┘
```

---

## 6. Dashboard Data Flow

```
┌─────────────────────────────────┐
│  Next.js Frontend               │
│  ┌───────────────────────────┐  │
│  │  API Calls (axios)         │  │ ← Fetch data from FastAPI
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Zustand Stores            │  │ ← Client-side state management
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  UI Components (shadcn/ui) │  │ ← Render with TailwindCSS
│  └───────────────────────────┘  │
│                                  │
│  ┌───────────────────────────┐  │
│  │  WebSocket (real-time)     │  │ ← Live updates
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## 7. Observability Flow

```
Application Events
    │
    ├──▶ OpenTelemetry Tracing ──▶ Jaeger/Zipkin (planned)
    │
    ├──▶ Prometheus Metrics ──▶ Prometheus Server ──▶ Grafana Dashboards
    │
    ├──▶ JSON Structured Logging ──▶ Promtail ──▶ Loki ──▶ Grafana Explore
    │
    └──▶ Alert Rules ──▶ Prometheus AlertManager ──▶ Notifications
```

---

**Version**: 3.0.0
**Last Updated**: 2026-05-17
