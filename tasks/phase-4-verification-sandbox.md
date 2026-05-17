# PHASE 4 — VERIFICATION SANDBOX (HYBRID) (2–3 tuần)

## Mục tiêu
Không tin AI. Chỉ tin execution result.
Build verification pipeline với 2 chế độ: Dev (OpenCode) + Prod (Docker).

## Tech Stack
| Thành phần | Tech |
|---|---|
| Dev Mode | OpenCode tools (bash, edit, write, read) |
| Prod Mode | Docker, Ubuntu |
| CI | GitHub Actions |
| Logs | Loki |

---

## 4.1. Verification Pipeline Core

### Mô tả
Pipeline kiểm chứng code: lint → unit test → integration test → build → security scan.

### Tasks
- [X] **4.1.1** — Implement verification pipeline service
  - File: `services/orchestrator/services/verification_service.py`
  - Function: `run_pipeline(code_path, mode) -> pipeline_result`
  - Steps: lint → unit_test → integration_test → build → security_scan
- [X] **4.1.2** — Implement lint step
  - Run linter (ruff, eslint, etc.)
  - Capture lint errors, warnings
  - Function: `run_lint(code_path) -> lint_result`
- [X] **4.1.3** — Implement unit test step
  - Run unit tests (pytest, jest, etc.)
  - Capture test results (pass/fail/skip)
  - Function: `run_unit_tests(code_path) -> test_result`
- [X] **4.1.4** — Implement integration test step
  - Run integration tests
  - Capture test results
  - Function: `run_integration_tests(code_path) -> test_result`
- [X] **4.1.5** — Implement build step
  - Run build command (npm build, docker build, etc.)
  - Capture build output, errors
  - Function: `run_build(code_path) -> build_result`
- [X] **4.1.6** — Implement security scan step
  - Run security scanner (bandit, npm audit, etc.)
  - Capture vulnerabilities
  - Function: `run_security_scan(code_path) -> security_result`
- [X] **4.1.7** — Implement pipeline orchestration
  - Run steps tuần tự hoặc song song
  - Stop nếu step quan trọng fail (fail-fast)
  - Function: `run_pipeline(code_path, steps) -> pipeline_result`
- [X] **4.1.8** — Implement pipeline result aggregation
  - Aggregate results từ tất cả steps
  - Calculate overall pass/fail
  - Function: `aggregate_results(step_results) -> overall_result`
- [X] **4.1.9** — Implement pipeline config
  - File: `services/orchestrator/config/pipeline_config.yaml`
  - Config: steps, order, fail_fast, timeout
- [X] **4.1.10** — Unit test cho verification pipeline
  - Test từng step
  - Test pipeline orchestration
  - Test fail-fast behavior
  - Test result aggregation

### Output
- Verification pipeline hoạt động
- 5 steps: lint, unit test, integration test, build, security scan
- Tests pass

---

## 4.2. OpenCode Verification (Dev Mode)

### Mô tả
Sử dụng OpenCode bash tool để chạy verification trong dev mode.

### Tasks
- [X] **4.2.1** — Implement OpenCode verification adapter
  - File: `services/execution/opencode_verification.py`
  - Function: `verify_dev_mode(code_path) -> verification_result`
  - Steps: delegate to OpenCode bash tool for each step
- [X] **4.2.2** — Implement bash tool delegation cho lint
  - Command: `ruff check .` hoặc `eslint .`
  - Capture: stdout, stderr, exit_code
- [X] **4.2.3** — Implement bash tool delegation cho tests
  - Command: `pytest tests/` hoặc `npm test`
  - Capture: test results, coverage
- [X] **4.2.4** — Implement bash tool delegation cho build
  - Command: `npm run build` hoặc `python -m build`
  - Capture: build output, errors
- [X] **4.2.5** — Implement bash tool delegation cho security scan
  - Command: `bandit -r .` hoặc `npm audit`
  - Capture: vulnerabilities
- [X] **4.2.6** — Implement timeout handling cho dev mode
  - Max execution time: 10 minutes
  - Auto-kill nếu vượt timeout
- [X] **4.2.7** — Implement result parsing cho dev mode
  - Parse exit code: 0 → VERIFIED, != 0 → FAILED
  - Extract error messages từ stdout/stderr
- [X] **4.2.8** — Unit test cho OpenCode verification
  - Test lint delegation
  - Test test delegation
  - Test build delegation
  - Test security scan delegation
  - Test timeout handling

### Output
- OpenCode verification (dev mode) hoạt động
- All 5 steps delegated via bash tool
- Tests pass

---

## 4.3. Docker Sandbox (Prod Mode)

### Mô tả
Quản lý Docker container để chạy code trong môi trường isolated cho production mode.

### Tasks
- [X] **4.3.1** — Implement Docker sandbox manager
  - File: `services/execution/sandbox_manager.py`
  - Function: `create_sandbox(image, resources) -> container_id`
  - Base image: Ubuntu với language runtimes
- [X] **4.3.2** — Implement mount repo vào container
  - Mount code vào container (read-only cho source, read-write cho output)
  - Function: `mount_repo(container_id, repo_path) -> mount_status`
- [X] **4.3.3** — Implement run verification trong container
  - Execute verification pipeline
  - Capture stdout, stderr, exit code
  - Function: `run_verification(container_id) -> verification_result`
- [X] **4.3.4** — Implement capture logs từ container
  - Collect container logs
  - Store logs với task_id reference
  - Function: `capture_logs(container_id) -> logs`
- [X] **4.3.5** — Implement destroy container sau khi hoàn thành
  - Clean up container sau khi verification xong
  - Function: `destroy_container(container_id) -> status`
- [X] **4.3.6** — Implement container timeout
  - Max execution time: 10 minutes
  - Auto-kill nếu vượt timeout
- [X] **4.3.7** — Implement resource limits (CPU, RAM) cho container
  - CPU: max 2 cores
  - RAM: max 4GB
- [X] **4.3.8** — Implement sandbox security
  - No network access (trừ khi cần)
  - No host filesystem access
  - No privileged mode
- [X] **4.3.9** — Unit test cho Docker sandbox
  - Test create container
  - Test mount repo
  - Test run verification
  - Test capture logs
  - Test destroy container
  - Test timeout
  - Test resource limits
  - Test security policy

### Output
- Docker sandbox (prod mode) hoạt động
- Security policy applied
- Tests pass

---

## 4.4. Exit Code Validation

### Mô tả
Parse exit code và test results để xác định verification status.

### Tasks
- [X] **4.4.1** — Implement exit code parsing
  - Rule: exit code = 0 → VERIFIED
  - Rule: exit code != 0 → FAILED
  - Function: `parse_exit_code(exit_code) -> status`
- [X] **4.4.2** — Implement error message extraction
  - Extract error messages từ stdout/stderr
  - Parse error type, location, description
  - Function: `extract_errors(output) -> errors`
- [X] **4.4.3** — Implement test result parsing
  - Parse test output (JUnit XML, TAP, etc.)
  - Extract: passed, failed, skipped, errors
  - Function: `parse_test_results(output) -> test_summary`
- [X] **4.4.4** — Implement verification status update
  - Update task status dựa trên verification result
  - Function: `update_verification_status(task_id, result) -> status`
- [X] **4.4.5** — Build API: POST /api/v1/tasks/{task_id}/verify
  - Input: { "code_path": "...", "mode": "dev|prod" }
  - Action: run pipeline, update status
  - Output: verification_result
- [X] **4.4.6** — Build API: GET /api/v1/tasks/{task_id}/verification-result
  - Output: verification_result + logs
- [X] **4.4.7** — Unit test cho exit code validation
  - Test exit code parsing
  - Test error extraction
  - Test test result parsing
  - Test status update

### Output
- Exit code validation hoạt động
- API verification
- Tests pass

---

## 4.5. Rollback Engine

### Mô tả
Rollback khi verification fail — revert branch, restore snapshot.

### Tasks
- [X] **4.5.1** — Implement revert branch function
  - Revert git branch về trạng thái trước khi code
  - Function: `revert_branch(task_id) -> revert_status`
- [X] **4.5.2** — Implement restore snapshot function
  - Restore database snapshot nếu cần
  - Function: `restore_snapshot(snapshot_id) -> restore_status`
- [X] **4.5.3** — Implement rollback trigger (verification fail)
  - Auto-trigger rollback khi verification fail
  - Function: `trigger_rollback(task_id, reason) -> rollback_record`
- [X] **4.5.4** — Implement rollback audit logging
  - Log rollback action, reason, result
  - Function: `log_rollback(rollback_record) -> audit_entry`
- [X] **4.5.5** — Build API: POST /api/v1/tasks/{task_id}/rollback
  - Input: { "reason": "..." }
  - Action: trigger rollback, log audit
  - Output: rollback_record
- [X] **4.5.6** — Implement rollback strategy config
  - File: `services/orchestrator/config/rollback_config.yaml`
  - Config: auto_rollback, manual_approval, max_rollbacks
- [X] **4.5.7** — Unit test cho rollback engine
  - Test revert branch
  - Test restore snapshot
  - Test auto-trigger
  - Test audit logging

### Output
- Rollback engine hoạt động
- Auto-rollback khi verification fail
- Tests pass

---

## 4.6. Mode Selection & Integration

### Mô tả
Tích hợp verification vào workflow — tự động chọn mode dựa trên risk level.

### Tasks
- [X] **4.6.1** — Implement mode selection service
  - File: `services/orchestrator/services/mode_selector.py`
  - Rule: risk LOW/MEDIUM → dev mode, HIGH/CRITICAL → prod mode
  - Function: `select_mode(task) -> mode`
- [X] **4.6.2** — Tích hợp verification vào workflow (node verify)
  - Connect verification service đến workflow verify node
  - Function: `verification_node(state) -> state`
- [X] **4.6.3** — Implement verification result → state update
  - Parse verification result, update task status
  - Function: `update_state_from_verification(result) -> state_update`
- [X] **4.6.4** — Implement verification fail → retry/escalate
  - Nếu verification fail → retry (max 2) hoặc escalate
  - Function: `handle_verification_fail(result) -> action`
- [X] **4.6.5** — Integration test: code → verify → update state
  - Tạo task mock với code
  - Chạy verification (dev mode)
  - Verify state update đúng
  - Test fail case

### Output
- Verification tích hợp vào workflow
- Auto mode selection
- State update từ verification result
- Integration tests pass

---

## 4.7. CI/CD Integration

### Mô tả
Tích hợp verification với CI/CD pipeline (GitHub Actions).

### Tasks
- [X] **4.7.1** — Setup GitHub Actions workflow
  - Tạo workflow file: `.github/workflows/verification.yml`
  - Stages: lint, test, build, security scan
- [X] **4.7.2** — Implement CI trigger từ workflow
  - LangGraph trigger CI pipeline
  - Function: `trigger_ci(task_id) -> pipeline_id`
- [X] **4.7.3** — Implement CI result callback
  - CI pipeline callback với kết quả
  - Function: `handle_ci_callback(pipeline_id, result) -> state_update`
- [X] **4.7.4** — Implement CI status tracking
  - Track CI pipeline status
  - Function: `get_ci_status(pipeline_id) -> status`
- [X] **4.7.5** — Test CI/CD integration
  - Trigger CI từ workflow
  - Verify callback
  - Verify state update

### Output
- CI/CD integration hoạt động
- Trigger + callback
- Tests pass

---

## Checklist Phase 4

| # | Task | Status | Notes |
|---|---|---|---|
| 4.1 | Verification Pipeline Core | ✅ | 5 steps |
| 4.2 | OpenCode Verification (Dev) | ✅ | Bash tool delegation |
| 4.3 | Docker Sandbox (Prod) | ✅ | Isolated container |
| 4.4 | Exit Code Validation | ✅ | Parse results |
| 4.5 | Rollback Engine | ✅ | Auto rollback |
| 4.6 | Mode Selection & Integration | ✅ | Risk-based mode |
| 4.7 | CI/CD Integration | ✅ | GitHub Actions |

**Definition of Done cho Phase 4:**
- [X] Verification pipeline hoạt động (5 steps)
- [X] Dev mode (OpenCode) hoạt động
- [X] Prod mode (Docker) hoạt động
- [X] Auto mode selection theo risk level
- [X] Có rollback khi fail
- [X] Integration tests pass
