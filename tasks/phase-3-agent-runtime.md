# PHASE 3 — AGENT RUNTIME (2–4 tuần)

## Mục tiêu
Build hệ agent thật — Dynamic Model Router (v4), prompt templates, context builder, OpenCode adapter, và 8 specialized agents.

## Tech Stack
| Thành phần | Tech |
|---|---|
| LLM Integration | LiteLLM (simple calls) + OpenCode (coding tools) |
| Models | DeepSeek V4 Flash, DeepSeek V4 Pro, Qwen 3.5 Plus, Qwen 3.6 Plus, MiniMax M2.7 |
| Model Router | Dynamic Model Router v4 (scoring: capability 40% + context 20% + speed 15% + cost 15% + circuit_breaker 10%) |
| Execution (Dev) | OpenCode tools (bash, edit, write, read, glob, grep) |
| Execution (Prod) | Docker sandbox |
| Context | Redis cache + PostgreSQL |
| Validation | Dual-Model Validation Gate (v4.1) |

---

## 3.1. Dynamic Model Router (v4)

### Mô tả
Sử dụng **Dynamic Model Router** từ Phase 0 — không gán cố định model cho agent.
Router tự động chọn model phù hợp nhất dựa trên scoring algorithm.

### Tasks
- [ ] **3.1.1** — Integrate Dynamic Model Router từ Phase 0
  - File: `shared/config/model_router.py` (đã có từ Phase 0)
  - Scoring: capability_match (40%) + context_fit (20%) + speed (15%) + cost (15%) + circuit_breaker (10%)
  - 5 models: DeepSeek V4 Flash, DeepSeek V4 Pro, Qwen 3.5 Plus, Qwen 3.6 Plus, MiniMax M2.7
- [ ] **3.1.2** — Implement task profile builder
  - File: `services/orchestrator/services/task_profile_builder.py`
  - Function: `build_task_profile(task_spec) -> TaskProfile`
  - Factors: task_type, complexity, context_size, speed_requirement, budget
  - Output: TaskProfile dùng cho Dynamic Model Router
- [ ] **3.1.3** — Implement model selection per agent call
  - Function: `select_model_for_agent(agent_name, task_profile) -> ModelSelection`
  - Returns: primary model + fallback chain + llm_path (litellm or opencode)
  - Uses model_capabilities.yaml capability registry
- [ ] **3.1.4** — Implement fallback mechanism (v4)
  - Fallback chains từ model_capabilities.yaml:
    - DeepSeek V4 Flash → MiniMax M2.7 → DeepSeek V4 Pro
    - DeepSeek V4 Pro → Qwen 3.6 Plus → MiniMax M2.7
    - Qwen 3.5 Plus → Qwen 3.6 Plus → DeepSeek V4 Pro
    - Qwen 3.6 Plus → No fallback (escalate to Mentor)
    - MiniMax M2.7 → DeepSeek V4 Flash → Qwen 3.5 Plus
  - Function: `get_fallback_chain(model_name) -> [fallback_models]`
- [ ] **3.1.5** — Implement circuit breaker integration
  - File: `shared/config/model_router.py` (đã có)
  - Per-model circuit breaker: closed → open → half-open
  - Thresholds: 3-5 failures, 30-90s recovery, 3 half-open max calls
  - Function: `is_model_available(model_name) -> bool`
- [ ] **3.1.6** — Implement validation routing (NEW v4.1)
  - Validator agent uses Qwen 3.5 Plus primary
  - Fallback: Qwen 3.6 Plus → DeepSeek V4 Pro
  - Function: `select_validator_model(task_profile) -> ModelSelection`
- [ ] **3.1.7** — Build API: POST /api/v1/models/select
  - Input: { "agent_name": "...", "task_spec": "..." }
  - Output: { "model": "...", "fallbacks": [...], "llm_path": "...", "estimated_cost": ... }
- [ ] **3.1.8** — Unit test cho Dynamic Model Router integration
  - Test task profile building
  - Test model selection per agent
  - Test fallback chains
  - Test circuit breaker integration
  - Test validation routing (v4.1)

### Output
- Dynamic Model Router v4 tích hợp hoàn chỉnh
- 5 models với scoring algorithm
- Fallback chains per model
- Circuit breaker integration
- Validation routing (v4.1)
- Tests pass

---

## 3.2. Agent Runtime Core

### Mô tả
Core functions để execute, retry, escalate, và takeover agents.

### Tasks
- [ ] **3.2.1** — Implement agent runtime service
  - File: `services/orchestrator/services/agent_runtime.py`
  - Function: `execute_agent(agent_name, task_spec, context) -> output`
  - Steps: build prompt → call model → parse response → validate output
- [ ] **3.2.2** — Implement retry_agent() function
  - Input: agent_name, task_spec, context, previous_output, error
  - Action: build retry prompt (include error), call model
  - Output: new_output
- [ ] **3.2.3** — Implement escalate_agent() function
  - Input: task_id, reason, context
  - Action: update task status = ESCALATED, notify mentor
  - Output: escalation_record
- [ ] **3.2.4** — Implement takeover() function
  - Input: task_id, mentor_id
  - Action: assign task to mentor, transfer context
  - Output: takeover_record
- [ ] **3.2.5** — Implement agent output parser
  - Parse model response: extract code, tests, docs
  - Validate output format
  - Function: `parse_agent_output(response) -> parsed_output`
- [ ] **3.2.6** — Implement agent cost tracking
  - Track tokens per agent call
  - Store trong cost_tracking table
  - Function: `track_cost(task_id, model, tokens) -> cost_record`
- [ ] **3.2.7** — Unit test cho agent runtime
  - Test execute_agent
  - Test retry_agent
  - Test escalate_agent
  - Test takeover
  - Test output parsing
  - Test cost tracking

### Output
- Agent runtime core hoạt động
- 4 core functions: execute, retry, escalate, takeover
- Tests pass

---

## 3.3. Prompt Templates

### Mô tả
Quản lý prompt templates cho từng agent — tách rời code, dễ update, dễ test.

### Tasks
- [ ] **3.3.1** — Load prompt templates từ Phase 0
  - Files: `agents/prompts/gatekeeper.txt`, `coder.txt`, `reviewer.txt`, `mentor.txt`, `devops.txt`, `monitoring.txt`, `orchestrator.txt`
  - 7 templates từ Phase 0
  - Verify templates có đầy đủ variables
- [ ] **3.3.2** — Tạo validator prompt template (NEW v4.1)
  - File: `agents/prompts/validator.txt`
  - Content: role (cross-validate classification), task, input format, output format
  - Variables: {user_request}, {gatekeeper_classification}, {project_context}
  - Output format: {verdict: APPROVED/REJECTED/NEEDS_REVIEW, confidence, reason, suggested_classification}
- [ ] **3.3.3** — Implement self-awareness prompts (v4)
  - Mỗi model nhận system prompt với: role, strengths, limitations, handoff protocol
  - Injected vào system prompt khi gọi model
  - File: `shared/config/model_capabilities.yaml` (đã có từ Phase 0)
- [ ] **3.3.4** — Implement prompt variable substitution
  - Function: `render_prompt(template_name, variables) -> rendered_prompt`
  - Support: {project_state}, {task_spec}, {laws}, {memory}, {agent_capabilities}
- [ ] **3.3.5** — Implement prompt versioning
  - Track prompt template versions
  - Function: `get_prompt_version(template_name) -> version`
  - A/B test prompts nếu cần
- [ ] **3.3.6** — Unit test cho prompt templates
  - Test load all templates
  - Test validator template (v4.1)
  - Test variable substitution
  - Test self-awareness injection
  - Test prompt versioning
  - Content: role, task, input format, output format, monitoring rules
  - Variables: {logs}, {metrics}, {baseline}
- [ ] **3.3.5** — Implement prompt renderer
  - File: `services/orchestrator/services/prompt_service.py`
  - Function: `render_prompt(template_name, variables) -> prompt_string`
  - Validate required variables
- [ ] **3.3.6** — Implement prompt versioning
  - Track prompt versions
  - Function: `get_prompt_version(template_name) -> version`
- [ ] **3.3.7** — Unit test cho prompt rendering
  - Test render từng template
  - Test missing variables
  - Test variable substitution

### Output
- 7 prompt templates (4 từ Phase 0 + 3 mới)
- Prompt renderer
- Tests pass

---

## 3.4. Context Builder

### Mô tả
Xây dựng context cho agent — chỉ load thông tin liên quan, không load toàn bộ project.

### Tasks
- [ ] **3.4.1** — Implement context builder service
  - File: `services/orchestrator/services/context_builder.py`
  - Function: `build_context(task_id) -> full_context`
  - Assembly: task + modules + memory + laws, trimmed
- [ ] **3.4.2** — Implement context: load task hiện tại
  - Query task registry
  - Include: title, description, expected_output, dependencies
  - Function: `load_task_context(task_id) -> task_context`
- [ ] **3.4.3** — Implement context: load related modules
  - Query module registry
  - Include: module name, status, interfaces, dependencies
  - Function: `load_module_context(module_id) -> module_context`
- [ ] **3.4.4** — Implement context: load relevant memory
  - Query instruction ledger + semantic retrieval
  - Include: past solutions, lessons learned, decisions
  - Function: `load_memory_context(task_spec) -> memory_context`
- [ ] **3.4.5** — Implement context: load architectural laws
  - Query laws.yaml
  - Include: applicable laws cho task hiện tại
  - Function: `load_laws_context(task_type) -> laws_context`
- [ ] **3.4.6** — Implement context size limit
  - Max tokens: 8000 (hoặc tùy model)
  - Priority: task_spec > laws > modules > memory
  - Function: `trim_context(context, max_tokens) -> trimmed_context`
- [ ] **3.4.7** — Unit test cho context builder
  - Test load task context
  - Test load module context
  - Test load memory context
  - Test context size limit
  - Test context assembly

### Output
- Context builder hoạt động
- Context size limit
- Tests pass

---

## 3.5. OpenCode Adapter (Dev Mode)

### Mô tả
Bridge giữa core orchestration và OpenCode execution tools cho dev mode.

### Tasks
- [ ] **3.5.1** — Implement OpenCode adapter service
  - File: `services/execution/opencode_adapter.py`
  - Function: `execute(task, context) -> execution_result`
  - Steps: create sub-agent → delegate tools → collect results
- [ ] **3.5.2** — Implement bash tool delegation
  - Delegate: run tests, lint, build commands
  - Function: `run_bash(command, timeout) -> result`
  - Capture: stdout, stderr, exit_code
- [ ] **3.5.3** — Implement file operation delegation
  - Delegate: read, edit, write, glob, grep
  - Function: `read_file(path) -> content`
  - Function: `write_file(path, content) -> status`
  - Function: `edit_file(path, old_string, new_string) -> status`
- [ ] **3.5.4** — Implement sub-agent management
  - Create sub-agent với task context
  - Monitor sub-agent execution
  - Handle sub-agent timeout
  - Function: `create_sub_agent(task, context) -> agent_id`
- [ ] **3.5.5** — Implement result collection
  - Collect: files_created, files_modified, test_results
  - Function: `collect_results(agent_id) -> execution_result`
- [ ] **3.5.6** — Implement error handling
  - Handle: command fail, timeout, file access error
  - Function: `handle_error(error) -> error_result`
- [ ] **3.5.7** — Unit test cho OpenCode adapter
  - Test bash delegation
  - Test file operations
  - Test sub-agent management
  - Test result collection
  - Test error handling

### Output
- OpenCode adapter hoạt động
- Tool delegation (bash, read, write, edit, glob, grep)
- Tests pass

---

## 3.6. Specialist Agent

### Mô tả
Agent thực thi chính — viết code, thiết kế module, xử lý logic, algorithm, build feature.

### Tasks
- [ ] **3.6.1** — Implement Specialist service
  - File: `services/orchestrator/services/specialist_service.py`
  - Function: `specialist_execute(task_spec, context) -> code_output`
  - Steps: build prompt → call model → parse code → validate
- [ ] **3.6.2** — Implement Specialist: viết code theo task
  - Input: task_spec + context
  - Output: code_files
  - Rule: tuân thủ architectural laws
- [ ] **3.6.3** — Implement Specialist: thiết kế module
  - Input: module_spec
  - Output: module_structure, interfaces, data_flow
- [ ] **3.6.4** — Implement Specialist: xử lý logic phức tạp
  - Input: logic_spec
  - Output: implementation + explanation
- [ ] **3.6.5** — Implement Specialist: xử lý algorithm
  - Input: algorithm_spec
  - Output: algorithm_implementation + complexity_analysis
- [ ] **3.6.6** — Implement rule: chỉ làm đúng scope
  - Validate output không vượt quá task_spec
  - Function: `validate_scope(output, task_spec) -> bool`
- [ ] **3.6.7** — Implement rule: không tự ý đổi kiến trúc
  - Check output không vi phạm architectural laws
  - Function: `check_architecture(output, laws) -> bool`
- [ ] **3.6.8** — Implement rule: nếu thiếu thông tin thì hỏi
  - Detect missing info trong task_spec
  - Output: question format ngắn gọn
- [ ] **3.6.9** — Implement rule: nếu task quá khó thì đánh dấu #ESCALATE
  - Detect complexity vượt quá capability
  - Output: #ESCALATE + reason
- [ ] **3.6.10** — Unit test cho Specialist Agent
  - Test code generation
  - Test module design
  - Test logic handling
  - Test algorithm handling
  - Test scope validation
  - Test architecture check
  - Test clarification request
  - Test escalation detection

### Output
- Specialist agent hoạt động
- 4 capabilities: code, design, logic, algorithm
- Rules enforcement
- Tests pass

---

## 3.7. Auditor Agent

### Mô tả
Bộ phận kiểm định độc lập — so code với spec, kiểm tra cấu trúc, kiến trúc, clean code, compliance.

### Tasks
- [ ] **3.7.1** — Implement Auditor service
  - File: `services/orchestrator/services/auditor_service.py`
  - Function: `auditor_review(code, spec, test_results, laws) -> verdict`
  - Steps: run checks → aggregate scores → decide verdict
- [ ] **3.7.2** — Implement Auditor: so code với spec
  - Input: code + spec
  - Check: code có implement đúng yêu cầu không
  - Output: match_score, missing_features, extra_features
- [ ] **3.7.3** — Implement Auditor: kiểm tra cấu trúc
  - Check: file structure, naming conventions, module organization
  - Output: structure_score, violations
- [ ] **3.7.4** — Implement Auditor: kiểm tra kiến trúc
  - Check: layer separation, dependency direction, design patterns
  - Output: architecture_score, violations
- [ ] **3.7.5** — Implement Auditor: kiểm tra clean code
  - Check: DRY, SOLID, readability, comments, error handling
  - Output: clean_code_score, suggestions
- [ ] **3.7.6** — Implement Auditor: kiểm tra compliance với architectural law
  - Check: từng law trong laws.yaml
  - Output: compliance_score, violations
- [ ] **3.7.7** — Implement Auditor: aggregate scores và verdict
  - Aggregate scores từ các checks trên
  - Threshold: >= 80% → APPROVED, 60-80% → REVISE, < 60% → ESCALATE
  - Function: `aggregate_scores(checks) -> verdict`
- [ ] **3.7.8** — Unit test cho Auditor Agent
  - Test spec match
  - Test structure check
  - Test architecture check
  - Test clean code check
  - Test laws compliance
  - Test quality verdict
  - Test output format

### Output
- Auditor agent hoạt động
- 5 audit checks
- Verdict: APPROVED / REVISE / ESCALATE
- Tests pass

---

## 3.8. Supreme Mentor Agent

### Mô tả
Cấp cao nhất — xử lý deadlock, quyết định chiến lược, giải quyết mâu thuẫn, final verdict.

### Tasks
- [ ] **3.8.1** — Implement Mentor service
  - File: `services/orchestrator/services/mentor_service.py`
  - Function: `mentor_process(task_id) -> verdict`
  - Steps: analyze history → identify root cause → decide → document
- [ ] **3.8.2** — Implement Mentor: xử lý deadlock
  - Detect deadlock: task blocked bởi dependency circular, retry loop
  - Function: `mentor_resolve_deadlock(task_id) -> solution`
- [ ] **3.8.3** — Implement Mentor: đưa ra quyết định chiến lược
  - Input: conflict_details (spec vs code vs review)
  - Function: `mentor_strategic_decision(conflict) -> decision`
- [ ] **3.8.4** — Implement Mentor: giải quyết mâu thuẫn
  - Input: spec, code, review_results
  - Function: `mentor_resolve_conflict(spec, code, review) -> resolution`
- [ ] **3.8.5** — Implement Mentor: refactor workflow
  - Detect workflow inefficiency
  - Function: `mentor_refactor_workflow(workflow_history) -> improvements`
- [ ] **3.8.6** — Implement Mentor: đưa ra final verdict
  - Input: task_history, retries, audits
  - Function: `mentor_final_verdict(task_id) -> verdict`
  - Output: APPROVED / REJECT / MODIFY
- [ ] **3.8.7** — Implement mentor quota management
  - Limit: max mentor calls per day (default: 10)
  - Track: mentor usage (Redis)
  - Function: `check_mentor_quota() -> can_call`
- [ ] **3.8.8** — Unit test cho Mentor Agent
  - Test deadlock resolution
  - Test strategic decision
  - Test conflict resolution
  - Test workflow refactor
  - Test final verdict
  - Test quota management

### Output
- Mentor agent hoạt động
- 5 capabilities: deadlock, strategy, conflict, refactor, verdict
- Quota management
- Tests pass

---

## 3.9. DevOps Agent

### Mô tả
Agent phụ trách build, deploy, CI/CD, monitoring logs, rollback.

### Tasks
- [ ] **3.9.1** — Implement DevOps service
  - File: `services/orchestrator/services/devops_service.py`
  - Function: `devops_execute(task, config) -> deployment_result`
- [ ] **3.9.2** — Implement DevOps: build image
  - Input: verified_code
  - Action: docker build
  - Output: image_tag
- [ ] **3.9.3** — Implement DevOps: deploy staging
  - Action: push image, deploy to staging
  - Output: deployment_url, status
- [ ] **3.9.4** — Implement DevOps: quản lý CI/CD
  - Trigger CI pipeline
  - Monitor CI status
- [ ] **3.9.5** — Implement DevOps: theo dõi logs
  - Collect logs từ containers
- [ ] **3.9.6** — Implement DevOps: rollback nếu cần
  - Action: revert to previous image
- [ ] **3.9.7** — Unit test cho DevOps Agent
  - Test build, deploy, CI trigger, log collection, rollback

### Output
- DevOps agent hoạt động
- 6 capabilities: build, run, deploy, CI, logs, rollback
- Tests pass

---

## 3.10. Monitoring Agent

### Mô tả
Agent theo dõi lỗi, phát hiện anomaly, cảnh báo regressions, gom feedback.

### Tasks
- [ ] **3.10.1** — Implement Monitoring service
  - File: `services/orchestrator/services/monitoring_service.py`
  - Function: `monitor_process() -> monitoring_result`
- [ ] **3.10.2** — Implement Monitoring: theo dõi lỗi
  - Collect errors từ logs
  - Group by type, frequency
- [ ] **3.10.3** — Implement Monitoring: phát hiện anomaly
  - Detect unusual patterns (spike in errors, latency)
- [ ] **3.10.4** — Implement Monitoring: cảnh báo regressions
  - Compare current metrics với baseline
- [ ] **3.10.5** — Implement Monitoring: gom feedback thành bug report
  - Collect user feedback, error logs
  - Generate bug report
- [ ] **3.10.6** — Implement Monitoring: hỗ trợ cải tiến hệ thống
  - Analyze trends, suggest improvements
- [ ] **3.10.7** — Unit test cho Monitoring Agent
  - Test error tracking, anomaly detection, regression, feedback, improvements

### Output
- Monitoring agent hoạt động
- 5 capabilities: errors, anomaly, regression, feedback, improvements
- Tests pass

---

## 3.11. Agent Integration Tests

### Mô tả
Test tích hợp toàn bộ agents trong workflow.

### Tasks
- [ ] **3.11.1** — Test: Gatekeeper → Validator → Orchestrator → Specialist → Auditor → Done
  - Tạo task mock
  - Chạy workflow với validation gate (v4.1)
  - Verify output đúng
- [ ] **3.11.2** — Test: Validation gate flow (Gatekeeper → Validator → Orchestrator)
  - Test APPROVED path (confidence ≥ 0.8)
  - Test reanalyze path (confidence < 0.8)
  - Test escalation path (REJECTED + HIGH risk)
  - Test skip validation (LOW risk + TRIVIAL complexity)
- [ ] **3.11.3** — Test: Escalation flow (Specialist fail → Mentor takeover)
  - Simulate Specialist fail 3 lần
  - Verify escalation → mentor takeover
  - Verify mentor resolves task
- [ ] **3.11.4** — Test: Dynamic Model Router v4
  - Tạo tasks với task_type khác nhau
  - Verify routing đúng model qua scoring algorithm
  - Test fallback chains
  - Test circuit breaker exclusion
- [ ] **3.11.5** — Test: Context builder với task phức tạp
  - Tạo task với nhiều dependencies
  - Verify context đầy đủ, không vượt token limit
- [ ] **3.11.6** — Test: OpenCode adapter (dev mode)
  - Tạo task mock
  - Delegate đến OpenCode tools
  - Verify execution result
- [ ] **3.11.7** — Test: Prompt templates
  - Test render prompts với variables
  - Test self-awareness injection (v4)
  - Verify prompt format đúng

### Output
- Integration tests pass
- Agents coordination ổn định
- Validation gate (v4.1) hoạt động
- Dynamic Model Router v4 hoạt động

---

## Checklist Phase 3

| # | Task | Status | Notes |
|---|---|---|---|
| 3.1 | Dynamic Model Router (v4) | ⬜ | Scoring, fallback, circuit breaker, validation routing |
| 3.2 | Agent Runtime Core | ⬜ | Execute, retry, escalate, takeover |
| 3.3 | Prompt Templates | ⬜ | 8 templates (7 + validator v4.1), self-awareness |
| 3.4 | Context Builder | ⬜ | Project state, memory, laws, dependencies |
| 3.5 | LLM Gateway | ⬜ | LiteLLM + OpenCode, cost tracking |
| 3.6 | Gatekeeper Agent | ⬜ | Classification, routing |
| 3.7 | Validator Agent | ⬜ | NEW v4.1: Cross-validation |
| 3.8 | Orchestrator Agent | ⬜ | Task breakdown, agent selection |
| 3.9 | Specialist Agent | ⬜ | Code generation, OpenCode tools |
| 3.10 | Auditor Agent | ⬜ | Code review, law compliance |
| 3.11 | Mentor Agent | ⬜ | Deadlock resolution, quota |
| 3.12 | DevOps Agent | ⬜ | Build, deploy, rollback |
| 3.13 | Monitoring Agent | ⬜ | Error tracking, anomaly detection |
| 3.14 | Agent Integration Tests | ⬜ | End-to-end, validation gate, DMR v4 |

**Definition of Done cho Phase 3:**
- [ ] 8 agents hoạt động (7 + Validator v4.1)
- [ ] Dynamic Model Router v4 tích hợp (5 models, scoring, fallback)
- [ ] Prompt templates hoàn chỉnh (8 templates + self-awareness)
- [ ] LLM Gateway hoạt động (LiteLLM + OpenCode)
- [ ] Integration tests pass
