# PHASE 5 — GOVERNANCE LAYER (2 tuần)

## Mục tiêu
"AI discipline" — ràng buộc AI bởi luật, confidence scoring, cost optimization.

## Tech Stack
| Thành phần | Tech |
|---|---|
| Law Engine | YAML parser + custom rules |
| Confidence | Custom scoring algorithm |
| Cost Tracking | Redis + PostgreSQL |

---

## 5.1. Confidence Engine

### Mô tả
Điểm tin cậy tính bằng dữ liệu thực tế, không cảm tính.
Công thức: `Confidence = (T × 0.35) + (L × 0.15) - (P × 0.20) + (A × 0.30)`

### Tasks
- [x] **5.1.1** — Implement test pass rate calculation (T)
  - Input: test_results (passed, total)
  - Output: T = passed / total (0-1)
  - Function: `calculate_test_pass_rate(test_results) -> T`
- [x] **5.1.2** — Implement lint/code quality score (L)
  - Input: lint_results (errors, warnings, total_checks)
  - Output: L = 1 - (errors + warnings*0.5) / total_checks (0-1)
  - Function: `calculate_lint_score(lint_results) -> L`
- [x] **5.1.3** — Implement retry penalty calculation (P)
  - Input: retry_count, max_retries
  - Output: P = retry_count / max_retries (0-1)
  - Function: `calculate_retry_penalty(retry_count, max_retries) -> P`
- [x] **5.1.4** — Implement architectural law compliance score (A)
  - Input: law_violations (total_laws, violated_laws)
  - Output: A = 1 - violated_laws / total_laws (0-1)
  - Function: `calculate_law_compliance(law_results) -> A`
- [x] **5.1.5** — Implement confidence scoring formula
  - Combine T, L, P, A theo công thức
  - Function: `calculate_confidence(T, L, P, A) -> confidence (0-1)`
- [x] **5.1.6** — Implement confidence threshold rules
  - >= 0.8 → auto approve
  - 0.6-0.8 → require review
  - < 0.6 → escalate
  - < 0.3 → takeover/rollback
  - Function: `decide_from_confidence(confidence) -> action`
- [x] **5.1.7** — Build API: GET /api/v1/tasks/{task_id}/confidence
  - Output: confidence_score + breakdown (T, L, P, A)
- [x] **5.1.8** — Implement confidence history tracking
  - Lưu confidence score mỗi lần calculate
  - Function: `log_confidence(task_id, confidence) -> history_entry`
- [x] **5.1.9** — Unit test cho confidence engine
  - Test từng component (T, L, P, A)
  - Test formula
  - Test threshold rules
  - Test history tracking

### Output
- Confidence engine hoạt động
- API confidence score
- Tests pass

---

## 5.2. Architectural Law Engine

### Mô tả
Kiểm tra code compliance với architectural laws từ laws.yaml.

### Tasks
- [x] **5.2.1** — Implement luật loader
  - Load laws từ `governance/laws.yaml` (Phase 0)
  - Parse thành rule objects
  - Function: `load_laws() -> laws`
- [x] **5.2.2** — Implement clean architecture checker
  - Check: layer separation, dependency direction
  - Rule: No business logic in controller
  - Rule: No direct DB access from UI
  - Function: `check_clean_architecture(code) -> violations`
- [x] **5.2.3** — Implement validation checker
  - Check: all APIs validate input
  - Rule: Pydantic/Zod validation present
  - Function: `check_validation(code) -> violations`
- [x] **5.2.4** — Implement forbidden patterns detector
  - Check: hardcoded secrets, eval(), raw SQL
  - Function: `detect_forbidden_patterns(code) -> violations`
- [x] **5.2.5** — Implement law violation reporting
  - Format: { law_id, law_name, severity, violation_details, location }
  - Function: `report_violations(violations) -> report`
- [x] **5.2.6** — Build API: GET /api/v1/laws
  - Output: List[laws] với status (active/inactive)
- [x] **5.2.7** — Build API: POST /api/v1/laws
  - Input: { id, name, description, severity, check_rule }
  - Output: created_law
- [x] **5.2.8** — Build API: GET /api/v1/tasks/{task_id}/law-violations
  - Output: List[law_violations] cho task đó
- [x] **5.2.9** — Unit test cho architectural law engine
  - Test law loading
  - Test clean architecture check
  - Test validation check
  - Test forbidden patterns
  - Test violation reporting

### Output
- Architectural law engine hoạt động
- API quản lý laws
- Tests pass

---

## 5.3. Cost Governor

### Mô tả
Giới hạn chi phí — theo dõi token usage, mentor calls, retry loops.

### Tasks
- [x] **5.3.1** — Implement token usage tracking
  - Track tokens per model call (input + output)
  - Store trong cost_tracking table
  - Function: `track_tokens(model, input_tokens, output_tokens) -> usage`
- [x] **5.3.2** — Implement mentor calls tracking
  - Track số lần gọi Mentor per day
  - Function: `track_mentor_call() -> count`
- [x] **5.3.3** — Implement retry loop tracking
  - Track retry loops per task
  - Detect infinite retry loops
  - Function: `track_retry_loop(task_id) -> loop_detected`
- [x] **5.3.4** — Implement daily mentor call limit
  - Limit: max 10 mentor calls per day (configurable)
  - Function: `check_mentor_limit() -> can_call`
- [x] **5.3.5** — Implement cost alerting
  - Alert khi cost vượt threshold (daily, weekly)
  - Function: `check_cost_alerts() -> alerts`
- [x] **5.3.6** — Implement cost governor rules
  - Rule: task nhỏ → Flash, trung bình → Pro, lớn → Mentor (nếu còn quota)
  - Function: `apply_cost_governance(task) -> model_selection`
- [x] **5.3.7** — Build API: GET /api/v1/cost-stats
  - Output: daily/weekly/monthly cost breakdown
- [x] **5.3.8** — Build API: GET /api/v1/cost-stats/{project_id}
  - Output: cost breakdown cho project
- [x] **5.3.9** — Unit test cho cost governor
  - Test token tracking
  - Test mentor call tracking
  - Test retry loop detection
  - Test mentor limit
  - Test cost alerts
  - Test cost governance rules

### Output
- Cost governor hoạt động
- Token tracking, mentor limit, cost alerts
- Tests pass

---

## 5.4. Risk Classification

### Mô tả
Phân loại rủi ro của task — quyết định action tương ứng.

### Tasks
- [x] **5.4.1** — Implement risk classification algorithm
  - Factors: complexity, data_sensitivity, user_impact, deployment_scope
  - Score: 1-10
  - Function: `calculate_risk_score(task) -> score`
- [x] **5.4.2** — Implement risk levels
  - LOW (1-3): auto approve
  - MEDIUM (4-6): require audit
  - HIGH (7-8): require senior review
  - CRITICAL (9-10): require human approval
  - Function: `classify_risk(score) -> risk_level`
- [x] **5.4.3** — Implement action mapping
  - LOW → auto approve, skip audit
  - MEDIUM → require audit
  - HIGH → require senior review + audit
  - CRITICAL → require human approval
  - Function: `get_risk_action(risk_level) -> action`
- [x] **5.4.4** — Implement risk scoring cho task
  - Calculate risk khi tạo task
  - Update risk khi task thay đổi
  - Function: `update_task_risk(task_id) -> risk_level`
- [x] **5.4.5** — Build API: GET /api/v1/tasks/{task_id}/risk
  - Output: risk_level, risk_score, factors
- [x] **5.4.6** — Implement risk-based workflow routing
  - Route task dựa trên risk level
  - LOW → fast track, CRITICAL → full review + human approval
  - Function: `route_by_risk(task) -> workflow_path`
- [x] **5.4.7** — Unit test cho risk classification
  - Test risk scoring
  - Test risk levels
  - Test action mapping
  - Test workflow routing

### Output
- Risk classification hoạt động
- Risk-based workflow routing
- Tests pass

---

## 5.5. Governance Integration

### Mô tả
Tích hợp toàn bộ governance components vào workflow.

### Tasks
- [x] **5.5.1** — Tích hợp confidence engine vào workflow
  - Calculate confidence sau verification
  - Use confidence để quyết định next action
- [x] **5.5.2** — Tích hợp architectural law engine vào Auditor node
  - Auditor gọi law engine để check compliance
- [x] **5.5.3** — Tích hợp cost governor vào model router
  - Model router gọi cost governor để check quota
- [x] **5.5.4** — Tích hợp risk classification vào task assignment
  - Assign task dựa trên risk level
- [x] **5.5.5** — Tích hợp risk level vào mode selection
  - Risk LOW/MEDIUM → dev mode, HIGH/CRITICAL → prod mode
- [x] **5.5.6** — Integration test: governance layer end-to-end
  - Tạo task → chạy workflow → verify governance checks
  - Test confidence threshold
  - Test law violations
  - Test cost limits
  - Test risk routing

### Output
- Governance layer tích hợp hoàn chỉnh
- Integration tests pass

---

## Checklist Phase 5

| # | Task | Status | Notes |
|---|---|---|---|
| 5.1 | Confidence Engine | ✅ | Formula: T×0.35 + L×0.15 - P×0.20 + A×0.30, clamped [0,1] |
| 5.2 | Architectural Law Engine | ✅ | Load từ laws.yaml, 3 checkers, violation reporting |
| 5.3 | Cost Governor | ✅ | Token tracking, mentor limit, cost alerts, model governance |
| 5.4 | Risk Classification | ✅ | LOW/MEDIUM/HIGH/CRITICAL, workflow routing |
| 5.5 | Governance Integration | ✅ | E2E tests: confidence+law+cost+risk pipeline |

**Definition of Done cho Phase 5:**
- [x] Confidence engine hoạt động
- [x] Law engine hoạt động
- [x] Cost governor hoạt động
- [x] Risk classification hoạt động
- [x] Integration tests pass
