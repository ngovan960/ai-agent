# Architecture Change Log — v2 → v3

## Metadata
- **From Version**: 2.0.0 (OpenCode-Centric)
- **To Version**: 3.0.0 (FastAPI-Centric)
- **Date**: 2026-05-15
- **Reason**: OpenCode is a coding agent tool, not an orchestration platform. FastAPI backend is better suited for brain role.

---

## 1. Core Architecture Change

### Before (v2)
```
OpenCode = Central Brain
├── Orchestrates all agents
├── Manages state machine
├── Dispatches tasks
├── Tracks costs
└── Logs audits
```

### After (v3)
```
FastAPI = Central Brain
├── Orchestrates all agents
├── Manages state machine
├── Dispatches tasks
├── Tracks costs
└── Logs audits

OpenCode = LLM + Tool Provider
├── Provides LLM access (DeepSeek, Qwen)
└── Provides tool execution (bash, edit, write, read, glob, grep)
```

### Lý do thay đổi
1. OpenCode là CLI coding agent — không được thiết kế để orchestrate multiple agents
2. OpenCode không thể manage state machine lifecycle
3. OpenCode không thể run concurrent workflows
4. FastAPI phù hợp hơn cho orchestration: async, type-safe, scalable
5. Tách biệt rõ ràng giữa orchestration (FastAPI) và execution (OpenCode)

---

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `ARCHITECTURE.md` | Rewrite | Updated all sections to reflect FastAPI as brain |
| `docs/opencode-architecture.md` | Complete rewrite | OpenCode as LLM + Tool Provider, not brain |
| `specs/opencode_adapter.yaml` | Rename + Update | Renamed to `opencode_integration.yaml`, updated role |
| `docs/llm-integration.md` | Update | Added 2-path LLM Gateway (LiteLLM + OpenCode) |
| `docs/data-flow.md` | Update | Updated LLM call flow and component integration |
| `README.md` | Update | Updated overview, directory structure, version |

---

## 3. Files NOT Changed

| File | Reason |
|---|---|
| `shared/config/state_transitions.py` | State machine logic correct |
| `database/schema.sql` | Schema correct |
| `governance/laws.yaml` | 20 laws correct |
| `docs/state-machine.md` | State machine spec correct |
| `docs/api-specification.md` | API design correct |
| `docs/testing-strategy.md` | Testing approach correct |
| `docs/security-design.md` | Security design correct |
| `docs/error-handling-resilience.md` | Resilience design correct |
| `docs/non-functional-requirements.md` | NFRs correct |
| `docs/risk-assessment.md` | Risk assessment correct |
| `docs/agent-matrix.md` | Agent matrix correct |
| `shared/config/models.yaml` | Model config correct |
| `agents/prompts/*.txt` (7 files) | Prompt templates correct |
| `specs/gatekeeper.yaml` | Agent spec correct |
| `specs/orchestrator.yaml` | Agent spec correct |
| `specs/specialist.yaml` | Agent spec correct |
| `specs/auditor.yaml` | Agent spec correct |
| `specs/mentor.yaml` | Agent spec correct |
| `specs/devops.yaml` | Agent spec correct |
| `specs/monitoring.yaml` | Agent spec correct |

---

## 4. Key Changes Summary

| Aspect | v2 | v3 |
|---|---|---|
| Brain | OpenCode | FastAPI backend |
| OpenCode role | Central brain | LLM + Tool Provider |
| LLM calls | All via OpenCode | LiteLLM (simple) + OpenCode (coding) |
| State machine | OpenCode manages | FastAPI engine |
| Agent dispatch | OpenCode calls agents | FastAPI router dispatch |
| Cost tracking | OpenCode calculates | FastAPI cost tracker |
| Audit logging | OpenCode logs | FastAPI audit middleware |
| Circuit breaker | OpenCode handles | FastAPI circuit breaker |

---

## 5. Impact on Implementation

### Phase 1 (Core State System)
- **No impact** — State machine, database schema, APIs remain the same
- **New**: FastAPI LLM Gateway service will be created in Phase 3

### Phase 2 (Workflow Engine)
- **Impact**: Workflow engine now runs in FastAPI, not OpenCode
- **New**: Agent router service in FastAPI

### Phase 3 (Agent Runtime)
- **Major impact**: Agents now called via FastAPI LLM Gateway
- **New**: OpenCode integration service (replaces OpenCode adapter)
- **New**: LiteLLM integration for simple agents

### Phase 4+ (Verification, Governance, Memory, etc.)
- **No impact** — These layers remain the same

---

## 6. Migration Notes

### For Developers
1. Update all references from "OpenCode as brain" to "FastAPI as brain"
2. Update `specs/opencode_adapter.yaml` → `specs/opencode_integration.yaml`
3. Update LLM call flow to use 2-path gateway
4. Update architecture diagrams in documentation

### For Code Implementation
1. Create FastAPI LLM Gateway service
2. Create LiteLLM integration for simple agents
3. Create OpenCode integration service for coding agents
4. Update agent dispatch to use FastAPI router

---

## 7. Benefits of v3 Architecture

1. **Clear separation of concerns**: FastAPI = orchestration, OpenCode = execution
2. **Better scalability**: FastAPI can scale independently of OpenCode
3. **Easier testing**: Each component can be tested in isolation
4. **More flexible**: Can swap OpenCode for other tool providers if needed
5. **Cost control**: FastAPI tracks all LLM costs centrally
6. **Audit trail**: FastAPI logs all actions to database
7. **Resilience**: FastAPI circuit breaker protects against LLM failures

---

## 8. Version History

| Version | Date | Description |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial design (self-built orchestration) |
| 2.0.0 | 2026-05-14 | OpenCode as central brain |
| 3.0.0 | 2026-05-15 | FastAPI as brain, OpenCode as LLM + Tool Provider |
