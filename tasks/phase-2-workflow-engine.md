# PHASE 2 — WORKFLOW ENGINE (2–3 tuần)

## Mục tiêu
Build orchestration engine — bộ não điều phối toàn hệ thống.
Workflow chạy end-to-end từ nhận task đến hoàn thành.

## Tech Stack
| Thành phần | Tech |
|---|---|
| Workflow Engine | Python State Machine (tự build) |
| State Store | PostgreSQL (Phase 1) |
| Queue | Redis (Phase 1) |
| Execution | OpenCode adapter (dev) + Docker sandbox (prod) |
| Models | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus, MiniMax M2.7 |

---

## 2.1. Workflow Engine Core

### Mô tả
Build workflow engine tự động điều phối tasks qua các states.
Workflow chạy end-to-end với **LLM Gateway**, **Agent Dispatcher**, và **Workflow Engine**.

### Tasks
- [x] **2.1.1** — Thiết kế workflow engine architecture
  - File: `services/orchestrator/services/workflow_engine.py`
  - Components: WorkflowEngine, NodeExecutor (8 state-based nodes), StateUpdater, AuditLogger
  - Pattern: Async event-driven state machine with per-state retry tracking
  - Flow: NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
  - v5.0.0: Full workflow orchestration with LLM Gateway integration
- [x] **2.1.2** — Implement WorkflowRunner
  - Function: `run_workflow(task_id) -> WorkflowResult`
  - Logic: read task state → determine next node → execute → update state → repeat
  - Async implementation with `asyncio.wait_for(timeout=1800s)`
  - Per-state retry tracking (`retries_per_state` dict) — prevents infinite loop bug
  - Max 2 retries per state before escalation
- [x] **2.1.3** — Implement LLM Gateway (NEW v5.0.0)
  - File: `services/orchestrator/services/llm_gateway.py`
  - Features: Circuit breaker per model, retry with backoff+jitter, fallback chains, cost tracking, rate limiting
  - 5 models: deepseek_v4_flash, deepseek_v4_pro, qwen_3_5_plus, qwen_3_6_plus, minimax_m2_7
  - Fallback chains per model, agent-specific default routing
  - Shared components: `shared/llm/circuit_breaker.py`, `retry_handler.py`, `cost_tracker.py`, `rate_limiter.py`
- [x] **2.1.4** — Implement Agent Dispatcher
  - File: `services/orchestrator/services/agent_dispatcher.py`
  - 7 agents: gatekeeper, orchestrator, specialist, auditor, mentor, devops, monitoring
  - State→Agent mapping (STATE_AGENT_MAP)
  - Per-agent model configs (AGENT_CONFIG)
  - Prompt template rendering via PromptTemplateLoader
  - Helper methods: dispatch_gatekeeper, dispatch_orchestrator, dispatch_specialist, dispatch_auditor, dispatch_mentor
- [x] **2.1.5** — Implement Prompt Templates
  - File: `services/orchestrator/services/prompt_templates.py`
  - Template loader with `.txt` files in `agents/prompts/`
  - Variable substitution, system prompt wrapping, context sections
  - All 7 agents have default templates
- [x] **2.1.6** — Implement StateUpdater
  - Function: `_transition_task(task, new_status, reason)`
  - Uses state_transitions.py từ Phase 0
  - Creates audit log entry per node execution
  - Optimistic lock conflict handling
- [x] **2.1.7** — Implement Workflow REST API
  - File: `services/orchestrator/routers/workflow.py`
  - Endpoints: POST /api/v1/workflows/execute, GET /api/v1/workflows/{task_id}/status, POST /api/v1/workflows/{task_id}/cancel, POST /api/v1/workflows/{task_id}/retry
  - Background task execution with `asyncio.Lock`-protected `_executions` dict
  - Cancellation support, retry with state reset
- [x] **2.1.8** — Unit test cho workflow engine
  - File: `tests/test_workflow_engine.py` — 25 tests
  - File: `tests/test_circuit_breaker.py` — 15 tests
  - File: `tests/test_llm_gateway.py` — 26 tests
  - File: `tests/test_agent_dispatcher.py` — 21 tests
  - Total: 87 new tests, 202 tests overall

### Output
- [x] Workflow engine hoạt động với 8 state-based nodes
- [x] LLM Gateway với circuit breaker, retry, fallback, cost tracking
- [x] Agent Dispatcher với 7 agents, state-based routing
- [x] Prompt Templates cho tất cả agents
- [x] Workflow REST API với background execution
- [x] 87 tests mới, 202 tests tổng, 73% coverage

---

## 2.2. Workflow Nodes Implementation

### Mô tả
Implement logic thật cho từng node trong workflow. Các node được cài đặt inline trong `WorkflowEngine` class (không tạo file riêng trong `nodes/`).

### Tasks
- [x] **2.2.1** — Implement node: Gatekeeper (`_node_gatekeeper`)
  - File: `services/orchestrator/services/workflow_engine.py:157`
  - Input: task (description, project_id)
  - Action: gọi `dispatcher.dispatch_gatekeeper()` → Gatekeeper phân loại task
  - Output: NodeResult (NEW → ANALYZING)
- [x] **2.2.2** — Implement node: Orchestrator (`_node_orchestrator`)
  - File: `services/orchestrator/services/workflow_engine.py:171`
  - Input: task (title, description, priority)
  - Action: gọi `dispatcher.dispatch_orchestrator()` → Orchestrator lập kế hoạch
  - Output: NodeResult (ANALYZING → PLANNING / PLANNING → IMPLEMENTING)
- [x] **2.2.3** — Implement node: Specialist (`_node_specialist`)
  - File: `services/orchestrator/services/workflow_engine.py:190`
  - Input: task (title, description, expected_output)
  - Action: gọi `dispatcher.dispatch_specialist()` → Specialist sinh code
  - Output: NodeResult (IMPLEMENTING → VERIFYING)
- [x] **2.2.4** — Implement node: Verification (`_node_verification`)
  - File: `services/orchestrator/services/workflow_engine.py:207`
  - V5.0.0: Placeholder node (pass-through VERIFYING → REVIEWING)
  - Full Docker sandbox verification deferred to Phase 4
  - Output: NodeResult (VERIFYING → REVIEWING)
- [x] **2.2.5** — Implement node: Auditor (`_node_auditor`)
  - File: `services/orchestrator/services/workflow_engine.py:214`
  - Input: task (code, spec, test_results)
  - Action: gọi `dispatcher.dispatch_auditor()` → Auditor review code
  - Decision: APPROVED → DONE, REVISE → IMPLEMENTING, ESCALATE → ESCALATED
  - Output: NodeResult (REVIEWING → DONE/IMPLEMENTING/ESCALATED)
- [x] **2.2.6** — Implement node: Mentor (`_node_mentor`)
  - File: `services/orchestrator/services/workflow_engine.py:230`
  - Input: task (history, conflict_details)
  - Action: gọi `dispatcher.dispatch_mentor()` → Mentor takeover
  - Decision: REJECT/FAILED → FAILED, otherwise → PLANNING
  - Output: NodeResult (ESCALATED → PLANNING/FAILED)
- [x] **2.2.7** — Implement node: Blocked (`_node_blocked`)
  - File: `services/orchestrator/services/workflow_engine.py:245`
  - V5.0.1: Pass-through node — task stays BLOCKED (stuck_task_detector handles escalation)
  - Output: NodeResult (BLOCKED → None)
- [x] **2.2.8** — Implement node: Default (`_node_default`)
  - File: `services/orchestrator/services/workflow_engine.py:252`
  - Fallback handler for unknown states
  - Output: NodeResult (failed, no handler for state)

### Output
- [x] 8 workflow nodes hoạt động (inline trong WorkflowEngine)
- [x] Mỗi node kết nối với AgentDispatcher để gọi LLM agent tương ứng
- [x] V5.0.1: BLOCKED node pass-through (stuck_task_detector handles escalation)

---

## 2.3. Dependency Management

### Mô tả
Quản lý dependencies giữa tasks — task B chỉ chạy khi task A hoàn thành.

### Tasks
- [x] **2.3.1** — Implement dependency graph service
  - File: `services/orchestrator/services/dependency_service.py`
  - build_dependency_graph(), can_start(), has_circular_dependency()
- [x] **2.3.2** — Implement dependency check logic
  - can_start(): kiểm tra tất cả dependencies có status = DONE
- [x] **2.3.3** — Build API: GET /api/v1/tasks/{task_id}/dependencies
  - File: `services/orchestrator/routers/tasks.py`
- [x] **2.3.4** — Build API: POST /api/v1/tasks/{task_id}/dependencies
  - With circular dependency detection (DFS)
- [x] **2.3.5** — Implement circular dependency detection
  - DFS cycle detection in dependency graph
- [x] **2.3.6** — Implement dependency resolution trigger
  - post_transition_hook: khi task → DONE, auto-trigger dependent BLOCKED tasks
  - File: `services/orchestrator/services/tasks.py`
- [x] **2.3.7** — Unit test cho dependency management
  - File: `tests/test_phase2_full.py` — TestDependencyManagement (8 tests)

### Output
- [x] Dependency graph service hoạt động
- [x] Circular dependency detection
- [x] Auto-trigger khi dependency resolved
- [x] Tests pass

---

## 2.4. Escalation Engine

### Mô tả
Xử lý escalation khi task thất bại nhiều lần — chuyển lên cấp cao hơn.

### Tasks
- [x] **2.4.1** — Implement escalation logic trong workflow engine
  - Rule: retry > 2 → ESCALATE
  - File: `services/orchestrator/services/workflow_engine.py:95-115`
  - Per-state retry tracking (`retries_per_state` dict)
  - V5.0.1: BLOCKED → ESCALATED handled by `stuck_task_detector.py`
- [x] **2.4.2** — Implement Mentor escalation (`_node_mentor`)
  - File: `services/orchestrator/services/workflow_engine.py:230`
  - Mentor receives task history + conflict details via `dispatcher.dispatch_mentor()`
  - Routing: REJECT/FAILED → FAILED, otherwise → PLANNING
- [x] **2.4.3** — Build API: POST /api/v1/workflows/{task_id}/retry
  - File: `services/orchestrator/routers/workflow.py`
  - Reset retry count, re-run workflow
- [x] **2.4.4** — Implement escalation notification
  - File: `services/orchestrator/services/escalation_service.py`
  - Audit logging, queue statistics, logger warnings
- [x] **2.4.5** — Implement escalation priority queue
  - File: `services/orchestrator/services/escalation_service.py`
  - EscalationPriorityQueue với push/pop/peek/remove
  - Sắp xếp theo risk_level rank (CRITICAL > HIGH > MEDIUM > LOW)
- [x] **2.4.6** — Unit test cho escalation
  - File: `tests/test_phase2_full.py` — TestEscalation (7 tests)

### Output
- [x] Auto-escalation khi retry > 2 per state
- [x] Mentor node handles escalated tasks with takeover logic
- [x] Workflow retry API endpoint
- [x] Escalation notification + priority queue — DONE

---

## 2.5. Takeover Mode

### Mô tả
Mentor takeover khi task bị escalate — mentor rewrite, redesign, override execution.

### Tasks
- [x] **2.5.1** — Implement Mentor takeover trong workflow engine
  - File: `services/orchestrator/services/workflow_engine.py:230` (`_node_mentor`)
  - Mentor receives: task history (retries, status), conflict details (failure_reason)
  - Calls `dispatcher.dispatch_mentor()` → LLM-powered decision
  - Decision: REJECT/FAILED → FAILED (final), otherwise → PLANNING (restart planning)
- [x] **2.5.2** — Mentor rewrite capability
  - Via dispatcher → LLM Gateway → Qwen 3.6 Plus model
  - Prompt template: `agents/prompts/mentor.txt`
  - Output: verdict (REWRITE/REDESIGN/OVERRIDE/REJECT/FAILED)
- [x] **2.5.3** — Implement Mentor redesign capability
  - File: `services/orchestrator/services/mentor_service.py`
  - Action: REDESIGN → ESCALATED → PLANNING
- [x] **2.5.4** — Implement Mentor override execution
  - File: `services/orchestrator/services/mentor_service.py`
  - Action: OVERRIDE → ESCALATED → VERIFYING (skip implementation)
- [x] **2.5.5** — Build API: POST /api/v1/tasks/{task_id}/takeover
  - File: `services/orchestrator/routers/workflow.py`
  - Input: mentor_id, action (rewrite|redesign|override|reject|approve), reason
  - Output: updated_task + mentor_decision
- [x] **2.5.6** — Implement mentor decision logging
  - File: `services/orchestrator/services/mentor_service.py`
  - MentorInstruction table + AuditLog
  - Quota tracking (check + record calls)
- [x] **2.5.7** — Unit test cho takeover mode
  - File: `tests/test_phase2_full.py` — TestMentorTakeover (7 tests)

### Output
- [x] Mentor takeover đầy đủ (rewrite/redesign/override/reject/approve)
- [x] Decision logging + audit trail
- [x] Mentor quota enforcement (10 calls/day)
- [x] API endpoint: POST /api/v1/tasks/{task_id}/takeover

---

## 2.6. Workflow Orchestration

### Mô tả
Kết nối toàn bộ nodes thành workflow hoàn chỉnh, xử lý lỗi, timeout, recovery.

### Tasks
- [x] **2.6.1** — Kết nối toàn bộ nodes thành workflow
  - File: `services/orchestrator/services/workflow_engine.py`
  - `_run_node()` routes state → node method (8 nodes)
  - `_run_workflow_loop()` iterates until terminal state
- [x] **2.6.2** — Implement error handling trong workflow
  - Mỗi node try/except — failure → retry (max 2 per state) → escalate
  - Non-retryable errors → skip model (circuit breaker opens)
- [x] **2.6.3** — Implement timeout handling
  - `asyncio.wait_for(timeout=1800s)` — 30 min toàn workflow
  - GATEWAY_DEFAULT_TIMEOUT = 60s per LLM call
  - Per-model timeouts: 15-90s
- [x] **2.6.4** — Implement workflow recovery
  - File: `services/orchestrator/routers/workflow.py`
  - POST /api/v1/workflows/{task_id}/retry — reset từ state hiện tại
  - POST /api/v1/workflows/execute — re-run workflow
- [x] **2.6.5** — Implement workflow status tracking
  - GET /api/v1/workflows/{task_id}/status — WorkflowResult
  - Returns: status, nodes completed, cost, latency, errors
- [x] **2.6.6** — Implement workflow cancel
  - POST /api/v1/workflows/{task_id}/cancel — transition to CANCELLED
- [x] **2.6.7** — Integration test: end-to-end workflow
  - File: `tests/test_phase2_full.py` — TestDependencyManagement, TestEscalation, TestMentorTakeover
  - File: `tests/test_registry.py` — TestStateTransitionHooks, TestTaskRegistry, TestModuleRegistry, TestProjectRegistry
  - File: `tests/test_state_transitions.py` — TestValidatingState

### Output
- [x] Workflow hoàn chỉnh chạy end-to-end (8 nodes, retry, escalate)
- [x] Error handling, timeout 30min, cancel support
- [x] Workflow REST API: execute/status/cancel/retry
- [x] Integration tests — 275 tests pass, 76% coverage

---

## 2.7. Gatekeeper Agent Integration

### Mô tả
Tích hợp Gatekeeper agent vào workflow engine — node đầu tiên phân loại task.

### Tasks
- [x] **2.7.1** — Implement Gatekeeper service (via AgentDispatcher)
  - File: `services/orchestrator/services/agent_dispatcher.py:180` (`dispatch_gatekeeper()`)
  - Model: DeepSeek V4 Flash (primary), fallback MiniMax M2.7 → DeepSeek V4 Pro
  - Output: GatekeeperClassification parsed from JSON response
- [x] **2.7.2** — Implement Gatekeeper node trong workflow engine
  - File: `services/orchestrator/services/workflow_engine.py:157` (`_node_gatekeeper`)
  - Input: task.description as user_request
  - Output: NodeResult (NEW → ANALYZING)
- [x] **2.7.3** — Prompt template cho Gatekeeper
  - File: `agents/prompts/gatekeeper.txt`
  - System prompt wrapper via `prompt_templates.py`
- [x] **2.7.4** — Unit test cho Gatekeeper
  - File: `tests/test_agent_dispatcher.py` — dispatch_gatekeeper test
  - File: `tests/test_workflow_engine.py` — gatekeeper node test

### Output
- [x] Gatekeeper agent hoạt động (AgentDispatcher + LLM Gateway)
- [x] Tích hợp vào workflow (_node_gatekeeper)
- [x] Tests pass

---

## 2.8. Validator Agent Integration (v4.1)

### Mô tả
Validation service từ Phase 1 — cross-validate Gatekeeper classification. Validation hoạt động độc lập qua API, không phải node riêng trong workflow engine.

### Tasks
- [x] **2.8.1** — Implement Validator service (Phase 1)
  - File: `services/orchestrator/services/validation.py`
  - Function: `validate_classification()`, `should_skip_validation()`
  - Model: Qwen 3.5 Plus
- [x] **2.8.2** — Validation API endpoints (Phase 1)
  - POST /api/v1/validation/ — full validation
  - POST /api/v1/validation/quick — quick validation
  - GET /api/v1/validation/should-skip — skip check
- [x] **2.8.3** — State machine validation gatecheck (Phase 1)
  - `validate_transition_with_gatecheck()` trong state_transitions.py v3
  - Skip condition: Risk=LOW AND Complexity=TRIVIAL/SIMPLE
- [x] **2.8.4** — Tích hợp Validator thành node riêng trong workflow
  - File: `services/orchestrator/services/workflow_engine.py` — `_node_validator`
  - 12th state: VALIDATING added to TaskStatus enum, state_transitions, and node_map
  - NEW → VALIDATING (skip if LOW+TRIVIAL) → ANALYZING (approved) / ESCALATED (rejected)

### Output
- [x] Validator service + API (Phase 1)
- [x] State machine gatecheck rules (Phase 1)
- [x] Workflow node integration — VALIDATING node in workflow engine

---

## 2.9. Orchestrator Agent Integration

### Mô tả
Tích hợp Orchestrator agent vào workflow engine — lập kế hoạch và điều phối task.

### Tasks
- [x] **2.9.1** — Implement Orchestrator service (via AgentDispatcher)
  - File: `services/orchestrator/services/agent_dispatcher.py:200` (`dispatch_orchestrator()`)
  - Model: Qwen 3.6 Plus (primary), fallback DeepSeek V4 Pro → Qwen 3.5 Plus
  - Input: classified_task + project_state
  - Output: Orchestrator plan parsed from JSON
- [x] **2.9.2** — Implement Orchestrator node trong workflow engine
  - File: `services/orchestrator/services/workflow_engine.py:171` (`_node_orchestrator`)
  - Handles both ANALYZING → PLANNING and PLANNING → IMPLEMENTING transitions
  - Input: task (title, description, priority)
- [x] **2.9.3** — Prompt template cho Orchestrator
  - File: `agents/prompts/orchestrator.txt`
- [x] **2.9.4** — Unit test cho Orchestrator
  - File: `tests/test_agent_dispatcher.py` — dispatch_orchestrator test
  - File: `tests/test_workflow_engine.py` — orchestrator node tests

### Output
- [x] Orchestrator agent hoạt động (AgentDispatcher + LLM Gateway)
- [x] Tích hợp vào workflow (_node_orchestrator, 2 state transitions)
- [x] Tests pass

---

## Checklist Phase 2

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Workflow Engine Core | ✅ 100% | WorkflowEngine, LLM Gateway, AgentDispatcher, Prompt Templates, Workflow API |
| 2.2 | Workflow Nodes | ✅ 100% | 9 nodes (added VALIDATING): gatekeeper, validator, orchestrator, specialist, verification, auditor, mentor, blocked, default |
| 2.3 | Dependency Management | ✅ 100% | Dependency graph, circular detection (DFS), can_start, APIs, auto-trigger |
| 2.4 | Escalation Engine | ✅ 100% | Auto-escalate (retry>2), priority queue, notification, Mentor node, retry API |
| 2.5 | Takeover Mode | ✅ 100% | Rewrite/redesign/override/reject/approve, quota enforcement, decision logging, API |
| 2.6 | Workflow Orchestration | ✅ 100% | Error handling, 30min timeout, cancel, status tracking, retry API, integration tests |
| 2.7 | Gatekeeper Integration | ✅ 100% | _node_gatekeeper + dispatcher.dispatch_gatekeeper + prompt template |
| 2.8 | Validator Integration | ✅ 100% | VALIDATING state, _node_validator, NEW→VALIDATING→ANALYZING flow |
| 2.9 | Orchestrator Integration | ✅ 100% | _node_orchestrator + dispatcher.dispatch_orchestrator (2 state transitions) |

**Definition of Done cho Phase 2:**
- [x] Workflow engine chạy end-to-end (9 nodes, retry, escalation via LLM Gateway)
- [x] LLM Gateway với circuit breaker + retry + fallback + cost tracking
- [x] Agent Dispatcher với 7 agents, state-based routing, prompt templates
- [x] Workflow REST API: execute/status/cancel/retry/takeover/escalate (with `asyncio.Lock`)
- [x] Dependency Management: graph, circular detection (DFS), auto-trigger, APIs
- [x] Escalation Engine: auto-escalate, priority queue, notification
- [x] Mentor Takeover: rewrite/redesign/override/reject/approve, quota tracking
- [x] Validator Node: 12th state (VALIDATING), NEW→VALIDATING→ANALYZING flow
- [x] Workflow timeout 30min (`asyncio.wait_for`)
- [x] 73 new tests (275 tests tổng, 76% coverage)
- [x] 25 files created/modified
- [x] 6 bugs fixed from code review (v5.0.1)

**Version history:**
- v5.0.0: Phase 2 core — Workflow Engine, LLM Gateway, AgentDispatcher, Prompt Templates, Workflow API
- v5.0.1: Bug fixes — infinite retry loop, BLOCKED immediate escalation, race condition, unused imports, hardcoded auditor, missing timeout
- v5.1.0: Phase 1+2 completion — dependency management, escalation priority queue, mentor takeover, validator node, 73 new tests
