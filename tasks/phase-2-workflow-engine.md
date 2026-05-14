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
- [ ] **2.1.1** — Thiết kế workflow engine architecture
  - File: `services/orchestrator/services/workflow_engine.py`
  - Components: WorkflowRunner, NodeExecutor, EdgeRouter, StateUpdater
  - Pattern: Event-driven state machine
- [ ] **2.1.2** — Implement WorkflowRunner
  - Function: `run_workflow(task_id) -> workflow_result`
  - Logic: read task state → determine next node → execute → update state → repeat
  - Async implementation
- [ ] **2.1.3** — Implement NodeExecutor
  - Function: `execute_node(node_name, task_id, context) -> node_result`
  - Nodes: receive_task, plan, assign, execute, verify, review, done
  - Each node has: input, output, error_handler
- [ ] **2.1.4** — Implement EdgeRouter
  - Function: `route_edge(current_node, result) -> next_node`
  - Conditional routing based on node result
  - Rules: verify pass → review, verify fail → retry, review approve → done
- [ ] **2.1.5** — Implement StateUpdater
  - Function: `update_state(task_id, new_status, context) -> task`
  - Uses state_transitions.py từ Phase 0
  - Creates audit log entry
- [ ] **2.1.6** — Unit test cho workflow engine
  - Test run_workflow (happy path)
  - Test node execution
  - Test edge routing
  - Test state update
  - Test error handling

### Output
- Workflow engine hoạt động
- 5 core components
- Tests pass

---

## 2.2. Workflow Nodes Implementation

### Mô tả
Implement logic thật cho từng node trong workflow.

### Tasks
- [ ] **2.2.1** — Implement node: Receive Task (Intake)
  - File: `services/orchestrator/services/nodes/receive_task.py`
  - Input: user request (natural language)
  - Action: parse request, tạo task record với status = NEW
  - Output: task_id, task_spec
- [ ] **2.2.2** — Implement node: Plan (chia task, xác định dependency)
  - File: `services/orchestrator/services/nodes/plan.py`
  - Input: task_spec
  - Action: phân tích nghiệp vụ, chia thành subtasks, xác định dependencies
  - Output: task_breakdown_list, dependency_graph
- [ ] **2.2.3** — Implement node: Assign (giao task cho agent phù hợp)
  - File: `services/orchestrator/services/nodes/assign.py`
  - Input: task_breakdown
  - Action: chọn agent dựa trên complexity, priority, skill
  - Output: task → agent mapping
- [ ] **2.2.4** — Implement node: Execute (gọi execution layer)
  - File: `services/orchestrator/services/nodes/execute.py`
  - Input: task + assigned agent
  - Action: gọi execution adapter (OpenCode hoặc Docker)
  - Output: code, tests, documentation
- [ ] **2.2.5** — Implement node: Verify (chạy verification pipeline)
  - File: `services/orchestrator/services/nodes/verify.py`
  - Input: code + tests
  - Action: chạy verification (lint, test, build, security scan)
  - Output: verification_result (pass/fail), logs
- [ ] **2.2.6** — Implement node: Review (Auditor kiểm tra)
  - File: `services/orchestrator/services/nodes/review.py`
  - Input: code + spec + verification_result
  - Action: auditor review (so code với spec, check laws, clean code)
  - Output: APPROVED / REVISE / ESCALATE
- [ ] **2.2.7** — Implement node: Done (cập nhật state)
  - File: `services/orchestrator/services/nodes/done.py`
  - Input: approved_task
  - Action: update task status = DONE, log completion, trigger next tasks
  - Output: completed_task_record

### Output
- 7 workflow nodes hoạt động
- Mỗi node có unit test

---

## 2.3. Dependency Management

### Mô tả
Quản lý dependencies giữa tasks — task B chỉ chạy khi task A hoàn thành.

### Tasks
- [ ] **2.3.1** — Implement dependency graph service
  - File: `services/orchestrator/services/dependency_service.py`
  - Data structure: directed graph (adjacency list)
  - Function: `build_dependency_graph(task_ids) -> graph`
- [ ] **2.3.2** — Implement dependency check logic
  - Function: `can_start(task_id) -> bool`
  - Return True nếu tất cả dependencies có status = DONE
- [ ] **2.3.3** — Build API: GET /api/v1/tasks/{task_id}/dependencies
  - Output: List[dependency_tasks] với status của mỗi dependency
- [ ] **2.3.4** — Build API: POST /api/v1/tasks/{task_id}/dependencies
  - Input: { "dependency_ids": ["uuid1", "uuid2"] }
  - Validation: check circular dependency
- [ ] **2.3.5** — Implement circular dependency detection
  - Algorithm: DFS cycle detection
  - Function: `has_circular_dependency(task_id, dependency_ids) -> bool`
  - Raise error nếu circular
- [ ] **2.3.6** — Implement dependency resolution trigger
  - Khi task A → DONE, check các tasks phụ thuộc A
  - Nếu tất cả dependencies của task B → DONE, auto transition B từ BLOCKED → PLANNING
- [ ] **2.3.7** — Unit test cho dependency management
  - Test valid dependency chain
  - Test circular dependency detection
  - Test auto-trigger khi dependency resolved
  - Test blocked task

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
- [ ] **2.4.1** — Implement escalation service
  - File: `services/orchestrator/services/escalation_service.py`
  - Rule: retry > 2 → ESCALATE
  - Function: `should_escalate(task_id) -> bool`
  - Trigger: khi verify fail hoặc review = REVISE
- [ ] **2.4.2** — Build API: POST /api/v1/tasks/{task_id}/escalate
  - Input: { "reason": "...", "context": "..." }
  - Action: update task status = ESCALATED, tạo escalation record
  - Output: escalation_record
- [ ] **2.4.3** — Implement notification khi escalate
  - Gửi alert đến dashboard (WebSocket)
  - Log audit entry
  - (Optional) gửi email/Slack notification
- [ ] **2.4.4** — Implement escalation routing
  - Routing: ESCALATED → Mentor Agent
  - Function: `route_to_mentor(task_id) -> mentor_task`
  - Mentor nhận task + full context (history, retries, logs)
- [ ] **2.4.5** — Implement escalation priority queue
  - Task escalated được ưu tiên cao hơn task thường
  - Mentor queue: ưu tiên theo severity
  - Function: `get_escalation_queue() -> sorted_tasks`
- [ ] **2.4.6** — Unit test cho escalation engine
  - Test auto-escalate khi retry > 2
  - Test manual escalation
  - Test notification
  - Test routing to mentor
  - Test priority queue

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
- [ ] **2.5.1** — Implement Mentor takeover service
  - File: `services/orchestrator/services/mentor_service.py`
  - Function: `mentor_takeover(task_id) -> new_plan`
  - Mentor đọc: task_spec, code hiện tại, retry_history, audit_logs
  - Mentor quyết định: rewrite / redesign / fix / escalate further
- [ ] **2.5.2** — Implement Mentor rewrite capability
  - Mentor viết lại code từ đầu
  - Output: new_code + tests
  - Transition: ESCALATED → IMPLEMENTING (với owner = Mentor)
- [ ] **2.5.3** — Implement Mentor redesign capability
  - Mentor thay đổi thiết kế/module structure
  - Output: new_design + updated_task_breakdown
  - Transition: ESCALATED → PLANNING
- [ ] **2.5.4** — Implement Mentor override execution
  - Mentor bypass một số steps nếu cần
  - Ví dụ: skip verify nếu task đơn giản và mentor confidence cao
  - Log override decision
- [ ] **2.5.5** — Build API: POST /api/v1/tasks/{task_id}/takeover
  - Input: { "mentor_id": "...", "action": "rewrite|redesign|override", "reason": "..." }
  - Output: updated_task + mentor_decision
- [ ] **2.5.6** — Implement mentor decision logging
  - Lưu mentor decision vào mentor_instructions table
  - Lưu lesson learned
- [ ] **2.5.7** — Unit test cho takeover mode
  - Test mentor takeover
  - Test rewrite flow
  - Test redesign flow
  - Test override flow
  - Test decision logging

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
- [ ] **2.6.1** — Kết nối toàn bộ nodes thành workflow
  - Compile workflow với tất cả nodes
  - Test workflow với mock task
- [ ] **2.6.2** — Implement error handling trong workflow
  - Catch exceptions trong mỗi node
  - Log error, update task status = BLOCKED
  - Retry node nếu lỗi transient
- [ ] **2.6.3** — Implement timeout handling
  - Timeout per node: execute (10min), verify (5min), review (5min)
  - Function: `check_timeout(node, start_time) -> bool`
  - Nếu timeout → log error, transition to BLOCKED
- [ ] **2.6.4** — Implement workflow recovery (resume sau lỗi)
  - Lưu workflow state vào database (workflows table)
  - Function: `resume_workflow(workflow_id) -> state`
  - Resume từ node bị lỗi
- [ ] **2.6.5** — Implement workflow status tracking
  - API: GET /api/v1/workflows/{workflow_id}/status
  - Output: current_node, elapsed_time, nodes_completed, nodes_pending
- [ ] **2.6.6** — Implement workflow history
  - Lưu workflow execution history
  - Function: `get_workflow_history(workflow_id) -> history`
- [ ] **2.6.7** — Integration test: end-to-end workflow
  - Tạo task → chạy workflow → verify done
  - Test error handling (simulate node failure)
  - Test timeout handling
  - Test resume sau lỗi
  - Test escalation flow

### Output
- Workflow hoàn chỉnh chạy end-to-end
- Error handling, timeout, recovery
- Integration tests pass

---

## 2.7. Gatekeeper Agent Integration

### Mô tả
Tích hợp Gatekeeper agent vào workflow engine.

### Tasks
- [ ] **2.7.1** — Implement Gatekeeper service
  - File: `services/orchestrator/services/gatekeeper_service.py`
  - Function: `gatekeeper_process(user_request) -> classified_task`
  - Steps: parse request → lookup memory → classify complexity → route
- [ ] **2.7.2** — Implement Gatekeeper: nhận yêu cầu từ user
  - Input: natural language request
  - Function: `parse_request(request) -> parsed_request`
  - Parse: extract intent, entities, constraints
- [ ] **2.7.3** — Implement Gatekeeper: kiểm tra task đã từng làm chưa
  - Query task registry + memory
  - Function: `check_existing_task(parsed_request) -> existing_task | None`
  - Nếu có → return cached_solution
- [ ] **2.7.4** — Implement Gatekeeper: phân loại task theo độ khó
  - Scoring: complexity (1-10) dựa trên: scope, dependencies, risk
  - Function: `classify_complexity(parsed_request) -> { level, score }`
- [ ] **2.7.5** — Implement Gatekeeper: quyết định routing
  - Rule: easy → local agent, medium → specialist, hard → orchestrator plan
  - Function: `route_decision(complexity) -> routing_plan`
- [ ] **2.7.6** — Tích hợp Gatekeeper vào workflow (node receive_task)
  - Gatekeeper = node đầu tiên trong workflow
  - Output: parsed_request + complexity + routing_plan
- [ ] **2.7.7** — Unit test cho Gatekeeper
  - Test parse request
  - Test check existing task
  - Test classify complexity
  - Test route decision

### Output
- Gatekeeper agent hoạt động
- Tích hợp vào workflow
- Tests pass

---

## 2.8. Orchestrator Agent Integration

### Mô tả
Tích hợp Orchestrator agent vào workflow engine.

### Tasks
- [ ] **2.8.1** — Implement Orchestrator service
  - File: `services/orchestrator/services/orchestrator_service.py`
  - Function: `orchestrate(classified_task) -> workflow_plan`
  - Steps: get project state → breakdown task → select agents → create plan
- [ ] **2.8.2** — Implement Orchestrator: hiểu trạng thái dự án
  - Function: `get_project_state(project_id) -> project_state`
  - Query: modules status, tasks status, dependencies, blockers
- [ ] **2.8.3** — Implement Orchestrator: chia task thành các bước nhỏ
  - Input: task_spec + project_state
  - Output: task_breakdown_list (title, description, expected_output, dependencies)
  - Function: `breakdown_task(task_spec, project_state) -> subtasks`
- [ ] **2.8.4** — Implement Orchestrator: chọn agent phù hợp
  - Input: subtask + complexity
  - Output: agent_assignment (gatekeeper/specialist/auditor/mentor)
  - Function: `select_agent(subtask) -> agent_name`
- [ ] **2.8.5** — Implement Orchestrator: điều phối luồng làm việc
  - Function: `orchestrate(subtasks, assignments) -> workflow_plan`
  - Output: execution_order, parallel_tasks, dependencies
- [ ] **2.8.6** — Implement Orchestrator: quyết định next action
  - Rule: verify fail → retry (max 2), retry > 2 → escalate
  - Rule: review = REVISE → retry, review = ESCALATE → takeover
  - Function: `decide_next_action(task_result) -> action`
- [ ] **2.8.7** — Tích hợp Orchestrator vào workflow (nodes plan + assign)
  - Orchestrator = node "plan" + "assign" trong workflow
  - Output: workflow_plan + agent_assignments
- [ ] **2.8.8** — Unit test cho Orchestrator
  - Test get project state
  - Test breakdown task
  - Test select agent
  - Test orchestrate
  - Test decide next action

### Output
- Orchestrator agent hoạt động
- Tích hợp vào workflow
- Tests pass

---

## Checklist Phase 2

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Workflow Engine Core | ⬜ | State machine tự build |
| 2.2 | Workflow Nodes | ⬜ | 7 nodes |
| 2.3 | Dependency Management | ⬜ | Graph + circular detection |
| 2.4 | Escalation Engine | ⬜ | Auto-escalate khi retry > 2 |
| 2.5 | Takeover Mode | ⬜ | Mentor rewrite/redesign/override |
| 2.6 | Workflow Orchestration | ⬜ | Error handling, timeout, recovery |
| 2.7 | Gatekeeper Integration | ⬜ | Node đầu tiên |
| 2.8 | Orchestrator Integration | ⬜ | Plan + assign nodes |

**Definition of Done cho Phase 2:**
- [ ] Workflow engine chạy end-to-end
- [ ] 7 nodes hoạt động
- [ ] Retry & escalation hoạt động
- [ ] Agent coordination cơ bản chạy được
- [ ] Integration tests pass
