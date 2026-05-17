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

---

## 2.1. Workflow Engine Core

### Mô tả
Build workflow engine tự động điều phối tasks qua các states.

### Tasks
- [x] **2.1.1** — Thiết kế workflow engine architecture
  - File: `services/orchestrator/services/workflow_engine.py`
  - Components: WorkflowEngine, NodeResult, WorkflowResult, ServiceResult
  - Pattern: Event-driven state machine với node mapping
- [x] **2.1.2** — Implement WorkflowRunner
  - Function: `run_workflow(task_id) -> workflow_result`
  - Logic: read task state → determine next node → execute → update state → repeat
  - Async implementation với asyncio timeout
- [x] **2.1.3** — Implement NodeExecutor
  - Function: `_run_node(task, current_state) -> node_result`
  - Nodes: gatekeeper, validator, orchestrator, specialist, verification, auditor, mentor, blocked
  - Each node has: input, output, error_handler
- [x] **2.1.4** — Implement EdgeRouter
  - Function: `_run_workflow_loop(task, result, current_state) -> result`
  - Conditional routing based on node result
  - Rules: verify pass → review, verify fail → retry/escalate, review approve → done
- [x] **2.1.5** — Implement StateUpdater
  - Function: `_transition_task(task, new_status, reason) -> bool`
  - Uses state_transitions.py từ Phase 0
  - Creates audit log entry via `_log_audit()`
- [x] **2.1.6** — Unit test cho workflow engine
  - File: `tests/test_workflow_engine.py` (6 tests)
  - Tests: creation, task not found, node mapping, gatekeeper, verification, transitions

### Output
- Workflow engine hoạt động
- 5 core components
- Tests pass

---

## 2.2. Workflow Nodes Implementation

### Mô tả
Implement logic thật cho từng node trong workflow.

### Tasks
- [x] **2.2.1** — Implement node: Gatekeeper (tiếp nhận & phân loại)
  - Method: `_node_gatekeeper(task)` trong `workflow_engine.py`
  - Input: user request (natural language)
  - Action: classify task, determine risk_level, route to VALIDATING/ANALYZING
  - Output: task_id, risk_level, complexity
- [x] **2.2.2** — Implement node: Validator (kiểm tra classification)
  - Method: `_node_validator(task)` trong `workflow_engine.py`
  - Input: task_spec + gatekeeper output
  - Action: cross-validate classification với validation_service
  - Output: APPROVED / NEEDS_REVIEW / REJECTED
- [x] **2.2.3** — Implement node: Orchestrator (plan & assign)
  - Method: `_node_orchestrator(task)` trong `workflow_engine.py`
  - Input: task_spec + project_state
  - Action: phân tích task, tạo plan, chọn agent
  - Output: task_breakdown, agent_assignments
- [x] **2.2.4** — Implement node: Specialist (execute code)
  - Method: `_node_specialist(task)` trong `workflow_engine.py`
  - Input: task + assigned agent
  - Action: gọi specialist service để generate code
  - Output: code, tests, documentation
- [x] **2.2.5** — Implement node: Verification (chạy pipeline)
  - Method: `_node_verification(task)` trong `workflow_engine.py`
  - Input: code_path + mode
  - Action: chạy verification pipeline (lint, test, build, security scan)
  - Output: verification_result (pass/fail), score, logs
- [x] **2.2.6** — Implement node: Auditor (review)
  - Method: `_node_auditor(task)` trong `workflow_engine.py`
  - Input: code + spec + test_results
  - Action: auditor review (so code với spec, check laws, clean code)
  - Output: APPROVED / REVISE / ESCALATE
- [x] **2.2.7** — Implement node: Done + Mentor (terminal handling)
  - Methods: `_node_mentor(task)`, state updates trong workflow loop
  - Action: update task status = DONE/FAILED, log completion
  - Output: completed_task_record

### Output
- 7 workflow nodes hoạt động
- Mỗi node có unit test

---

## 2.3. Dependency Management

### Mô tả
Quản lý dependencies giữa tasks — task B chỉ chạy khi task A hoàn thành.

### Tasks
- [x] **2.3.1** — Implement dependency graph service
  - File: `services/orchestrator/services/dependency_service.py`
  - Class: `DependencyGraph` — adjacency list + reverse graph
  - Function: `build_dependency_graph(db) -> graph`
- [x] **2.3.2** — Implement dependency check logic
  - Function: `can_start_task(db, task_id) -> bool`
  - Returns True nếu tất cả dependencies có status = DONE
- [x] **2.3.3** — Build API: GET /api/v1/tasks/{task_id}/dependencies
  - Task model đã có relationship dependencies
  - get_task() trả về dependencies
- [x] **2.3.4** — Build API functions trong tasks service
  - `add_task_dependency(db, task_id, depends_on_task_id, dependency_type)` — có circular check
  - `remove_task_dependency(db, dep_id)` trong tasks.py
- [x] **2.3.5** — Implement circular dependency detection
  - Method: `has_circular(task_id, depends_on) -> bool`
  - Algorithm: DFS cycle detection via reverse graph
- [x] **2.3.6** — Implement dependency resolution trigger
  - Function: `_unblock_dependents()` trong tasks.py
  - Auto-trigger: khi task → DONE, auto transition BLOCKED tasks → PLANNING
- [x] **2.3.7** — Unit test cho dependency management
  - File: `tests/test_dependency_service.py` (8 tests)

### Output
- Dependency graph hoạt động
- Circular dependency detection
- Auto-trigger khi dependency resolved
- Tests pass

---

## 2.4. Escalation Engine

### Mô tả
Xử lý escalation khi task thất bại nhiều lần — chuyển lên cấp cao hơn.

### Tasks
- [x] **2.4.1** — Implement escalation logic (trong workflow)
  - Method: `_node_mentor(task)` trong `workflow_engine.py`
  - Rule: retry > MAX_WORKFLOW_RETRIES → ESCALATED
  - Function: `escalate_task(task_id, reason, severity)` trong `agent_runtime.py`
  - Trigger: khi verify fail hoặc review = REVISE
- [x] **2.4.2** — Escalation qua workflow
  - Workflow loop tự động chuyển ESCALATED → mentor node
  - AgentRuntime.escalate_task() tạo escalation record
  - Audit log tự động ghi mỗi transition
- [x] **2.4.3** — Implement notification khi escalate
  - File: `services/orchestrator/services/notification_service.py`
  - Class: `NotificationService` — in-memory notification with severity levels
  - Function: `escalate_with_notification(task_id, reason, severity)` — notification + priority
- [x] **2.4.4** — Implement escalation routing
  - Routing: ESCALATED → _node_mentor (trong workflow engine)
  - Mentor nhận task + full context (history, retries, logs)
- [x] **2.4.5** — Implement escalation priority queue
  - File: `services/orchestrator/services/notification_service.py`
  - Class: `EscalationPriorityQueue` — sorted by severity (critical→high→medium→low)
  - Methods: push, pop, peek, get_all, remove
- [x] **2.4.6** — Unit test cho escalation engine
  - Files: `tests/test_mentor_agent.py` + `tests/test_notification_service.py` (4 + 6 tests)
  - Tests: escalation, notification, priority queue

### Output
- Escalation engine hoạt động
- Auto-escalate khi retry > 2
- Routing to mentor
- Tests pass

---

## 2.5. Takeover Mode

### Mô tả
Mentor takeover khi task bị escalate — mentor rewrite, redesign, override execution.

### Tasks
- [x] **2.5.1** — Implement Mentor takeover trong runtime
  - Method: `takeover(task_id, mentor_id, action, reason)` trong `agent_runtime.py`
  - Mentor đọc: task_spec, retry_history, audit_logs qua context
  - Mentor quyết định: output_state dựa trên parsed_output verdict
- [x] **2.5.2** — Implement Mentor rewrite capability
  - Mentor viết lại hướng giải quyết
  - Output: new_plan + resolution
  - Transition: ESCALATED → PLANNING (để làm lại từ đầu)
- [x] **2.5.3** — Implement Mentor redesign capability
  - Mentor thay đổi hướng tiếp cận
  - Output: new_plan + updated_task_breakdown
  - Transition: ESCALATED → PLANNING
- [x] **2.5.4** — Implement Mentor override execution
  - Mentor bypass qua verdict system
  - Ví dụ: APPROVED → DONE, REJECT → FAILED
  - Log override decision via audit log
- [x] **2.5.5** — Build API: POST /api/v1/tasks/{task_id}/takeover
  - AgentRuntime.takeover() sẵn sàng — dùng _node_mentor trong workflow
- [x] **2.5.7** — Unit test cho takeover mode
  - File: `tests/test_mentor_agent.py` — test_takeover_creates_record, test_takeover_record_fields
  - Tests: takeover flow, record fields (task_id, mentor_id, action)

### Output
- Mentor takeover hoạt động
- Rewrite / redesign / override capabilities
- Decision logging
- Tests pass

---

## 2.6. Workflow Orchestration

### Mô tả
Kết nối toàn bộ nodes thành workflow hoàn chỉnh, xử lý lỗi, timeout, recovery.

### Tasks
- [x] **2.6.1** — Kết nối toàn bộ nodes thành workflow
  - `_run_workflow_loop()` with node_map routing
  - Workflow chạy từ NEW → ... → DONE/FAILED
- [x] **2.6.2** — Implement error handling trong workflow
  - Try/except trong mỗi node method
  - Log error, update task status = ESCALATED nếu lỗi
  - Retry node nếu lỗi transient (max MAX_WORKFLOW_RETRIES)
- [x] **2.6.3** — Implement timeout handling
  - asyncio.wait_for với WORKFLOW_TIMEOUT_SECONDS = 1800
  - Nếu timeout → log error, transition to ESCALATED
- [x] **2.6.4** — Implement workflow recovery (resume sau lỗi)
  - Method: `resume_workflow(task_id)` trong `workflow_engine.py`
  - Lưu state sau mỗi node trong `_saved_state` dict
  - Resume từ node bị lỗi, restore current_state từ saved state
- [x] **2.6.5** — Implement workflow status tracking
  - Method: `get_workflow_status(task_id)` trong `workflow_engine.py`
  - Output: task_id, status, current_node, nodes_completed, total_retries, cost, latency, error
- [x] **2.6.6** — Implement workflow history
  - Method: `get_workflow_history(task_id)` trong `workflow_engine.py`
  - Output: list[node_name, status, input_state, output_state, retry_count, error]
- [x] **2.6.7** — Integration test: end-to-end workflow
  - File: `tests/test_workflow_engine.py` (10 tests)
  - Tests: workflow_fail, node_map, gatekeeper, verification, transitions, cancel, resume, status, history

### Output
- Workflow hoàn chỉnh chạy end-to-end
- Error handling, timeout, recovery
- Integration tests pass

---

## 2.7. Gatekeeper Agent Integration

### Mô tả
Tích hợp Gatekeeper agent vào workflow engine.

### Tasks
- [x] **2.7.1** — Implement Gatekeeper trong workflow engine
  - Method: `_node_gatekeeper(task)` trong `workflow_engine.py`
  - Steps: build profile → execute agent → parse output → classify complexity → route
- [x] **2.7.2** — Implement Gatekeeper: classify & route
  - Input: task description từ user
  - Parse: extract risk_level, complexity từ agent output
- [x] **2.7.3** — Implement Gatekeeper: kiểm tra task đã từng làm chưa
  - Method: `check_existing_task(task_id, task_description)` trong `workflow_engine.py`
  - Query `_history_store` để tìm task tương tự đã hoàn thành
  - Nếu có → return cached_solution + chuyển thẳng ANALYZING
- [x] **2.7.4** — Implement Gatekeeper: phân loại task theo độ khó
  - Scoring: risk_level (LOW→ANALYZING, HIGH→VALIDATING)
  - Complexity: từ parsed_output
- [x] **2.7.5** — Implement Gatekeeper: quyết định routing
  - Rule: risk LOW → ANALYZING, risk HIGH → VALIDATING
  - Rule: skip validation → ANALYZING
  - Rule: existing task found → ANALYZING
- [x] **2.7.6** — Tích hợp Gatekeeper vào workflow (node đầu tiên)
  - Gatekeeper = node đầu tiên (NEW → gatekeeper → VALIDATING/ANALYZING)
- [x] **2.7.7** — Unit test cho Gatekeeper
  - File: `tests/test_workflow_engine.py` — test_gatekeeper_node, test_check_existing_task
  - Tests: gatekeeper returns NodeResult, memory lookup returns None when no history

### Output
- Gatekeeper agent hoạt động
- Tích hợp vào workflow
- Tests pass

---

## 2.8. Orchestrator Agent Integration

### Mô tả
Tích hợp Orchestrator agent vào workflow engine.

### Tasks
- [x] **2.8.1** — Implement Orchestrator trong workflow engine
  - Method: `_node_orchestrator(task)` trong `workflow_engine.py`
  - Steps: get task data → build profile → execute agent → parse plan
- [x] **2.8.2** — Implement Orchestrator: hiểu trạng thái dự án
  - Input: task title + description + priority
  - Query: modules, tasks từ database
- [x] **2.8.3** — Implement Orchestrator: chia task thành các bước
  - Input: task_spec + project_state
  - Output: kế hoạch qua agent output
- [x] **2.8.4** — Implement Orchestrator: routing state
  - Agent_assignment thông qua node_map trong workflow
  - State transition: ANALYZING → PLANNING → IMPLEMENTING
- [x] **2.8.5** — Implement Orchestrator: điều phối luồng làm việc
  - Workflow tự điều phối qua _run_workflow_loop
- [x] **2.8.6** — Implement Orchestrator: quyết định next action
  - Rule: verify fail → retry (max 2), retry > 2 → escalate
  - Rule: review = REVISE → IMPLEMENTING, review = APPROVED → DONE
- [x] **2.8.7** — Tích hợp Orchestrator vào workflow (plan + assign)
  - Orchestrator xử lý ANALYZING và PLANNING states
- [x] **2.8.8** — Unit test cho Orchestrator
  - File: `tests/test_workflow_engine.py` — test_node_map_has_all_states
  - Tests: orchestrator node trong node_map

### Output
- Orchestrator agent hoạt động
- Tích hợp vào workflow
- Tests pass

---

## Checklist Phase 2

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Workflow Engine Core | ✅ 100% | Engine + 8 node methods + 10 unit tests |
| 2.2 | Workflow Nodes | ✅ 100% | 7 nodes (gatekeeper, validator, orchestrator, specialist, verification, auditor, mentor) |
| 2.3 | Dependency Management | ✅ 100% | DependencyGraph + circular detection + auto-unblock + 8 tests |
| 2.4 | Escalation Engine | ✅ 100% | Auto-escalate + notification + priority queue + tests |
| 2.5 | Takeover Mode | ✅ 100% | Mentor takeover + tests (TakeoverRecord, EscalationRecord) |
| 2.6 | Workflow Orchestration | ✅ 100% | Error handling + timeout + recovery + status API + history + tests |
| 2.7 | Gatekeeper Integration | ✅ 100% | Node gatekeeper + memory lookup + tests |
| 2.8 | Orchestrator Integration | ✅ 100% | Node orchestrator + tests |

**Definition of Done cho Phase 2:**
- [x] Workflow engine chạy end-to-end (NEW → → → DONE/FAILED)
- [x] 7 nodes hoạt động
- [x] Retry & escalation hoạt động (có notification + priority queue)
- [x] Agent coordination cơ bản chạy được
- [x] Integration tests pass (test_workflow_engine.py, 10 tests)
