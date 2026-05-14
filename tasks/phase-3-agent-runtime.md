# PHASE 3 — AGENT RUNTIME (2–4 tuần)

## Mục tiêu
Build hệ agent thật — model routing, prompt templates, context builder, OpenCode adapter, và 7 specialized agents.

## Tech Stack
| Thành phần | Tech |
|---|---|
| LLM Integration | LiteLLM (unified API cho nhiều models) |
| Models | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus |
| Execution (Dev) | OpenCode tools (bash, edit, write, read, glob, grep) |
| Execution (Prod) | Docker sandbox |
| Context | Redis cache + PostgreSQL |

---

## 3.1. Model Router

### Mô tả
Routing task đến model phù hợp dựa trên complexity score — giảm cost, tăng hiệu quả.

### Tasks
- [ ] **3.1.1** — Implement complexity scoring service
  - File: `services/orchestrator/services/complexity_service.py`
  - Factors: estimated_lines_of_code, số_dependencies, risk_level, domain_complexity
  - Score: 1-10
  - Function: `calculate_complexity(task_spec) -> score`
- [ ] **3.1.2** — Implement model routing logic
  - File: `services/orchestrator/services/model_router.py`
  - Rule: complexity < 3 → Flash (nhanh, rẻ)
  - Rule: complexity 3-7 → Pro (mạnh về code)
  - Rule: complexity >= 7 → Qwen (reasoning tốt)
  - Function: `route_model(complexity_score) -> model_name`
- [ ] **3.1.3** — Implement model config loader
  - Load từ `shared/config/models.yaml` (Phase 0)
  - Config: model_name, api_endpoint, max_tokens, temperature, cost_per_token
- [ ] **3.1.4** — Implement fallback mechanism
  - Nếu model lỗi → chuyển sang model dự phòng
  - Rule: Flash fail → Pro, Pro fail → Qwen
  - Function: `fallback_model(primary_model) -> backup_model`
- [ ] **3.1.5** — Build API: POST /api/v1/models/select
  - Input: { "task_spec": "...", "complexity": 5 }
  - Output: { "model": "deepseek-v4-pro", "reason": "..." }
- [ ] **3.1.6** — Unit test cho model router
  - Test complexity scoring
  - Test routing logic
  - Test fallback mechanism
  - Test model config loading

### Output
- Model router hoạt động
- Fallback mechanism
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
  - Files: `agents/prompts/gatekeeper.txt`, `coder.txt`, `reviewer.txt`, `mentor.txt`
  - Verify templates có đầy đủ variables
- [ ] **3.3.2** — Tạo orchestrator prompt template
  - File: `agents/prompts/orchestrator.txt`
  - Content: role, task, input format, output format, orchestration rules
  - Variables: {project_state}, {task_breakdown}, {agent_capabilities}
- [ ] **3.3.3** — Tạo devops prompt template
  - File: `agents/prompts/devops.txt`
  - Content: role, task, input format, output format, deployment rules
  - Variables: {code_path}, {deployment_config}, {environment}
- [ ] **3.3.4** — Tạo monitoring prompt template
  - File: `agents/prompts/monitoring.txt`
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
- [ ] **3.11.1** — Test: Gatekeeper → Orchestrator → Specialist → Auditor → Done
  - Tạo task mock
  - Chạy workflow
  - Verify output đúng
- [ ] **3.11.2** — Test: Escalation flow (Specialist fail → Mentor takeover)
  - Simulate Specialist fail 3 lần
  - Verify escalation → mentor takeover
  - Verify mentor resolves task
- [ ] **3.11.3** — Test: Model routing theo complexity
  - Tạo tasks với complexity khác nhau
  - Verify routing đúng model
- [ ] **3.11.4** — Test: Context builder với task phức tạp
  - Tạo task với nhiều dependencies
  - Verify context đầy đủ, không vượt token limit
- [ ] **3.11.5** — Test: OpenCode adapter (dev mode)
  - Tạo task mock
  - Delegate đến OpenCode tools
  - Verify execution result
- [ ] **3.11.6** — Test: Prompt templates
  - Test render prompts với variables
  - Verify prompt format đúng

### Output
- Integration tests pass
- Agents coordination ổn định

---

## Checklist Phase 3

| # | Task | Status | Notes |
|---|---|---|---|
| 3.1 | Model Router | ⬜ | Complexity scoring + routing |
| 3.2 | Agent Runtime Core | ⬜ | execute, retry, escalate, takeover |
| 3.3 | Prompt Templates | ⬜ | 7 templates + renderer |
| 3.4 | Context Builder | ⬜ | Task + module + memory + laws |
| 3.5 | OpenCode Adapter | ⬜ | Dev mode execution |
| 3.6 | Specialist Agent | ⬜ | Code, design, logic, algorithm |
| 3.7 | Auditor Agent | ⬜ | 5 checks + verdict |
| 3.8 | Supreme Mentor Agent | ⬜ | Deadlock, strategy, conflict |
| 3.9 | DevOps Agent | ⬜ | Build, deploy, CI, rollback |
| 3.10 | Monitoring Agent | ⬜ | Errors, anomaly, regression |
| 3.11 | Agent Integration Tests | ⬜ | End-to-end workflow |

**Definition of Done cho Phase 3:**
- [ ] Agent execution chạy thật
- [ ] Routing theo complexity hoạt động
- [ ] OpenCode adapter (dev mode) hoạt động
- [ ] Retry & escalation ổn định
- [ ] Integration tests pass
