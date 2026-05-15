# PHASE 0 — SYSTEM DESIGN (1–2 tuần)

## Mục tiêu
Xác định toàn bộ nền tảng kiến trúc trước khi code:
- Luật hệ thống (Architectural Laws)
- Workflow state machine
- Agent responsibility matrix
- Database schema draft
- Model responsibilities
- Dynamic Model Router (v4)
- Dual-Model Validation Gate (v4.1)
- Governance rules

---

## 0.1. Architectural Laws

### Mô tả
Tạo hệ thống luật mà mọi agent phải tuân thủ. Không có lớp này AI sẽ dễ loạn, sửa lung tung, hoặc phá kiến trúc.

### Tasks
- [x] **0.1.1** — Tạo file `laws.yaml` / `laws.json`
  - Đường dẫn: `/governance/laws.yaml`
  - Định dạng YAML với cấu trúc: id, name, description, severity, check_rule
- [x] **0.1.2** — Định nghĩa LAW-001: No business logic in controller
  - Severity: high
  - Check rule: Controller chỉ được nhận request → gọi service → return response
- [x] **0.1.3** — Định nghĩa LAW-002: All APIs must validate input
  - Severity: high
  - Check rule: Mọi endpoint phải có validation layer (Pydantic)
- [x] **0.1.4** — Định nghĩa LAW-003: No direct DB access from UI
  - Severity: high
  - Check rule: UI chỉ gọi API, không có connection string hoặc query trực tiếp
- [x] **0.1.5** — Định nghĩa LAW-004: Critical actions require human approval
  - Severity: critical
  - Check rule: Deploy production, delete data, thay đổi schema phải có approval
- [x] **0.1.6** — Định nghĩa LAW-005 đến LAW-020
  - LAW-005: No hardcoded secrets
  - LAW-006: All errors must be logged
  - LAW-007: API response time < 3s
  - LAW-008: No agent modifies architecture without approval
  - LAW-009: No DONE status without verification
  - LAW-010: No infinite retry loops
  - LAW-011: Scope adherence required
  - LAW-012: All state changes must be audited
  - LAW-013: Dual-model validation required for MEDIUM+ risk tasks
  - LAW-014: Terminal states are immutable (DONE, FAILED, CANCELLED)
  - LAW-015: Circuit breaker must be enforced per model
  - LAW-016: Mentor quota enforced (10 calls/day)
  - LAW-017: All LLM calls tracked (cost, latency, tokens)
  - LAW-018: Agent role boundaries enforced (no cross-role execution)
  - LAW-019: Confidence score clamped to [0, 1]
  - LAW-020: Risk-based execution mode selection (LOW/MEDIUM → dev, HIGH/CRITICAL → docker)

### Output
- File `laws.yaml` hoàn chỉnh với 20 rules (4 critical, 8 high, 8 medium)
- File: `governance/laws.yaml`

---

## 0.2. Workflow State Machine

### Mô tả
Thiết kế state machine định nghĩa luồng đi của mọi task trong hệ thống.

### Tasks
- [x] **0.2.1** — Thiết kế state machine diagram
  - 11 states: NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
  - 3 terminal states: DONE, FAILED, CANCELLED (immutable)
  - 2 special states: ESCALATED, BLOCKED
  - File: `docs/state-machine.md`
- [x] **0.2.2** — Định nghĩa 22 valid transitions với điều kiện
  - NEW → ANALYZING: Gatekeeper đã phân loại + **Validator đã approve** (v4.1)
  - NEW → BLOCKED: Thiếu thông tin để phân tích
  - ANALYZING → PLANNING: Orchestrator đã chia task
  - ANALYZING → BLOCKED: Không thể phân tích do thiếu thông tin
  - ANALYZING → CANCELLED: User hủy task
  - PLANNING → IMPLEMENTING: Agent đã nhận task và context
  - PLANNING → BLOCKED: Dependency chưa hoàn thành
  - PLANNING → CANCELLED: User hủy task
  - IMPLEMENTING → VERIFYING: Code đã hoàn thành, đưa vào sandbox
  - IMPLEMENTING → BLOCKED: Thiếu thông tin để tiếp tục
  - IMPLEMENTING → FAILED: Lỗi không phục hồi được
  - VERIFYING → REVIEWING: Sandbox pass (lint, test, build, security)
  - VERIFYING → IMPLEMENTING: Sandbox fail, retry count < max_retries
  - VERIFYING → FAILED: Verification thất bại nghiêm trọng và đã hết retry
  - REVIEWING → DONE: Auditor approve (confidence >= threshold)
  - REVIEWING → IMPLEMENTING: Auditor revise (confidence < threshold)
  - REVIEWING → ESCALATED: Auditor escalate (critical violation)
  - REVIEWING → CANCELLED: User hủy task
  - ESCALATED → PLANNING: Mentor takeover, tạo plan mới
  - ESCALATED → FAILED: Mentor reject task
  - BLOCKED → PLANNING: Dependency đã hoàn thành
  - BLOCKED → CANCELLED: User hủy task
- [x] **0.2.3** — Xác định các transition không hợp lệ
  - DONE → ANY: Task đã hoàn thành, không được sửa đổi
  - FAILED → ANY: Task đã thất bại vĩnh viễn, không được chuyển
  - CANCELLED → ANY: Task đã hủy, không được chuyển
  - VERIFYING → PLANNING: Phải qua retry/escalate, không được quay lại planning
  - REVIEWING → PLANNING: Phải qua retry (IMPLEMENTING), không được skip verify
  - ESCALATED → IMPLEMENTING: Phải qua Mentor takeover (PLANNING)
  - BLOCKED → IMPLEMENTING: Phải qua PLANNING trước
  - NEW → DONE: Phải qua toàn bộ workflow trước
- [x] **0.2.4** — Implement state transition validation
  - File: `shared/config/state_transitions.py`
  - Functions: validate_transition(), is_terminal(), get_valid_transitions()
  - v3: Added validate_transition_with_gatecheck() cho dual-model validation

### Output
- File `shared/config/state_transitions.py` (v3)
- File `docs/state-machine.md`
- 11 states, 22 valid transitions, 3 terminal states

---

## 0.3. Agent Responsibility Matrix

### Mô tả
Định nghĩa rõ vai trò, trách nhiệm và model AI phù hợp cho từng agent.
Model được chọn động qua **Dynamic Model Router** (v4), không gán cố định.

### Tasks
- [x] **0.3.1** — Gatekeeper Agent
  - Trách nhiệm: Phân loại task, routing, tra cứu cache/memory
  - Model: DeepSeek V4 Flash (nhanh, rẻ)
  - Input: User request
  - Output: GatekeeperClassification (task_type, complexity, risk_level, effort)
  - LLM Path: LiteLLM
- [x] **0.3.2** — Validator Agent (NEW v4.1)
  - Trách nhiệm: Cross-validate Gatekeeper classification trước khi pass task
  - Model: Qwen 3.5 Plus (reasoning tốt để phát hiện lỗi)
  - Input: User request + Gatekeeper classification
  - Output: ValidatorVerdict (APPROVED/REJECTED/NEEDS_REVIEW, confidence, reason)
  - Decision matrix:
    - APPROVED ≥ 0.8 → Pass to Orchestrator
    - APPROVED < 0.8 → Gatekeeper re-analyze
    - REJECTED → Escalate to Mentor (HIGH/CRITICAL) hoặc re-analyze
  - Skip nếu: Risk=LOW AND Complexity=TRIVIAL/SIMPLE
  - LLM Path: LiteLLM
- [x] **0.3.3** — Orchestrator Agent
  - Trách nhiệm: Hiểu trạng thái dự án, chia task, chọn agent, điều phối workflow
  - Model: Qwen 3.6 Plus (mạnh nhất về reasoning)
  - Input: Validated classification
  - Output: Task breakdown + assignment plan
  - LLM Path: LiteLLM
- [x] **0.3.4** — Specialist Agent
  - Trách nhiệm: Viết code, thiết kế module, xử lý logic, algorithm, build feature
  - Model: DeepSeek V4 Pro (mạnh về code)
  - Input: Task spec
  - Output: Code + tests
  - Tools: bash, edit, write, read, glob, grep
  - LLM Path: OpenCode
- [x] **0.3.5** — Auditor Agent
  - Trách nhiệm: So code với spec, kiểm tra kiến trúc, clean code, compliance với law
  - Model: Qwen 3.5 Plus
  - Input: Code + spec + laws
  - Output: APPROVED / REVISE / ESCALATE
  - Tools: read-only + bash (chỉ chạy tests)
  - LLM Path: LiteLLM
- [x] **0.3.6** — Supreme Mentor Agent
  - Trách nhiệm: Xử lý deadlock, quyết định chiến lược, giải quyết mâu thuẫn, final verdict
  - Model: Qwen 3.6 Plus (mạnh nhất)
  - Trigger: Khi task fail > 2 lần hoặc hệ thống bế tắc
  - Quota: 10 calls/day (enforced via database)
  - Output: Final decision + lesson learned
  - LLM Path: LiteLLM
- [x] **0.3.7** — DevOps/Deployment Agent
  - Trách nhiệm: Build image, chạy Docker, deploy staging, quản lý CI/CD, rollback
  - Model: DeepSeek V4 Pro hoặc Flash tùy task
  - Input: Verified code
  - Output: Deployed service
  - Tools: bash, read
  - LLM Path: OpenCode
- [x] **0.3.8** — Monitoring/Maintenance Agent
  - Trách nhiệm: Theo dõi lỗi, phát hiện anomaly, cảnh báo regressions, gom feedback
  - Model: MiniMax M2.7 hoặc DeepSeek V4 Flash
  - Input: Logs + metrics
  - Output: Alert + bug report
  - LLM Path: LiteLLM

### Output
- File `docs/agent-matrix.md` với bảng tổng hợp 8 agents (7 + Validator)
- 7 prompt templates trong `agents/prompts/`

---

## 0.4. Dynamic Model Router (v4)

### Mô tả
Hệ thống **không gán cố định** model cho agent. Dynamic Model Router tự động chọn model phù hợp nhất.

### Tasks
- [x] **0.4.1** — Tạo capability registry
  - File: `shared/config/model_capabilities.yaml`
  - 5 models: DeepSeek V4 Flash, DeepSeek V4 Pro, Qwen 3.5 Plus, Qwen 3.6 Plus, MiniMax M2.7
  - Capability scores: code, reasoning, classification, review, planning, speed, cost
  - Strengths/weaknesses per model
  - Fallback chains per model
- [x] **0.4.2** — Implement Dynamic Model Router
  - File: `shared/config/model_router.py`
  - Scoring formula: capability (40%) + context (20%) + speed (15%) + cost (15%) + circuit_breaker (10%)
  - Context filtering: exclude models that can't handle task
  - Budget constraints: max_cost_per_call
  - Circuit breaker integration
- [x] **0.4.3** — Configure models.yaml v4
  - File: `shared/config/models.yaml`
  - 5 production models + 2 embedding models
  - Circuit breaker config per model (thresholds, recovery timeouts)
  - Retry config (max retries, backoff)
  - Mentor quota config (10 calls/day)
- [x] **0.4.4** — Default routing table
  - classification → DeepSeek V4 Flash → MiniMax M2.7 → DeepSeek V4 Pro
  - validation → Qwen 3.5 Plus → Qwen 3.6 Plus → DeepSeek V4 Pro
  - code_generation → DeepSeek V4 Pro → Qwen 3.6 Plus → MiniMax M2.7
  - review → Qwen 3.5 Plus → Qwen 3.6 Plus → DeepSeek V4 Pro
  - planning → Qwen 3.6 Plus → DeepSeek V4 Pro → Qwen 3.5 Plus
  - decision → Qwen 3.6 Plus → DeepSeek V4 Pro → MiniMax M2.7
  - monitoring → MiniMax M2.7 → DeepSeek V4 Flash → Qwen 3.5 Plus
- [x] **0.4.5** — Self-awareness prompts
  - Mỗi model nhận system prompt với: role, strengths, limitations, handoff protocol
  - File: `docs/dynamic-model-router.md` section 5

### Output
- File `shared/config/model_capabilities.yaml`
- File `shared/config/model_router.py`
- File `shared/config/models.yaml` (v4)
- File `docs/dynamic-model-router.md` (v4.1)

---

## 0.5. Database Schema Draft

### Mô tả
Thiết kế schema PostgreSQL cho toàn bộ hệ thống.

### Tasks
- [x] **0.5.1** — Schema: projects
  - Fields: id (UUID), name, description, status, tech_stack (JSONB), architecture, rules (JSONB), created_by (FK), created_at, updated_at
  - Relations: 1 project → many modules, many tasks, many decisions, many workflows
- [x] **0.5.2** — Schema: modules
  - Fields: id (UUID), project_id (FK), name, description, status, created_at, updated_at
  - Constraints: UNIQUE(project_id, name)
  - Relations: 1 module → many tasks, many dependencies
- [x] **0.5.3** — Schema: tasks
  - Fields: id (UUID), project_id (FK), module_id (FK), title, description, owner, priority, status, confidence [0,1], retries, max_retries, expected_output, risk_score [0,10], risk_level, cancellation_reason, failure_reason, created_by, completed_at, failed_at, cancelled_at
  - Relations: 1 task → many retries, many audit_logs, many outputs, many dependencies
  - CheckConstraints: confidence >= 0 AND <= 1, risk_score >= 0 AND <= 10
- [x] **0.5.4** — Schema: task_outputs (separate table)
  - Fields: id (UUID), task_id (FK), output_type, content (JSONB)
- [x] **0.5.5** — Schema: task_dependencies (junction table)
  - Fields: id (UUID), task_id (FK), depends_on_task_id (FK), dependency_type
  - Constraints: UNIQUE(task_id, depends_on_task_id), CHECK (task_id != depends_on_task_id)
- [x] **0.5.6** — Schema: module_dependencies (junction table)
  - Fields: id (UUID), module_id (FK), depends_on_module_id (FK)
- [x] **0.5.7** — Schema: retries
  - Fields: id (UUID), task_id (FK), attempt_number, reason, agent_name, output (JSONB), error_log
- [x] **0.5.8** — Schema: audit_logs
  - Fields: id (UUID), task_id (FK), action, actor, actor_type, input (JSONB), output (JSONB), result, message
- [x] **0.5.9** — Schema: mentor_instructions
  - Fields: id (UUID), task_id (FK), instruction_type, content, context (JSONB), applied (bool), embedding (pgvector)
- [x] **0.5.10** — Schema: mentor_quota
  - Fields: id (UUID), date (unique), calls_used, calls_limit (default 10)
- [x] **0.5.11** — Schema: decisions
  - Fields: id (UUID), project_id (FK), task_id (FK), decision, reason, context (JSONB), alternatives (JSONB), decided_by
- [x] **0.5.12** — Schema: workflows
  - Fields: id (UUID), project_id (FK), name, status, current_node, graph (JSONB), state (JSONB), started_at, completed_at, error
- [x] **0.5.13** — Schema: deployments
  - Fields: id (UUID), task_id (FK), environment, image_tag, status, url, logs, deployed_by, approved_by (FK)
- [x] **0.5.14** — Schema: cost_tracking
  - Fields: id (UUID), task_id (FK), project_id (FK), agent_name, model, input_tokens, output_tokens, cost_usd, latency_ms, status, error_message
- [x] **0.5.15** — Schema: llm_call_logs
  - Fields: id (UUID), task_id (FK), cost_tracking_id (FK), agent_name, model, prompt_hash, input_tokens, output_tokens, latency_ms, status, retry_count, circuit_breaker_triggered
- [x] **0.5.16** — Schema: circuit_breaker_state
  - Fields: id (UUID), model (unique), state, failure_count, last_failure_at, last_success_at, half_open_at
- [x] **0.5.17** — Schema: embedding_config
  - Fields: id (UUID), model_name (unique), provider, dimensions, cost_per_1k_input_tokens, cost_per_1k_output_tokens, is_active
- [x] **0.5.18** — Schema: users + api_keys (auth)
  - Users: id, username, email, hashed_password, full_name, role, is_active, last_login
  - API Keys: id, user_id (FK), name, key_hash, key_prefix, permissions (JSONB), expires_at, is_active
- [x] **0.5.19** — Views
  - v_task_summary: task + project_name + module_name + counts
  - v_cost_summary: cost aggregation by project, agent, model
- [x] **0.5.20** — Indexes + Triggers
  - 30+ indexes trên các fields hay query
  - updated_at triggers cho projects, modules, tasks, mentor_instructions, circuit_breaker_state
- [x] **0.5.21** — Extensions
  - pgvector (vector search)
  - uuid-ossp (UUID generation)

### Output
- File `database/schema.sql` (v2.0.0, 15+ tables, 30+ indexes, pgvector)
- 2 views: v_task_summary, v_cost_summary
- updated_at triggers

---

## 0.6. Documentation

### Mô tả
Viết tài liệu kiến trúc tổng thể để làm reference cho toàn bộ team/dev.

### Tasks
- [x] **0.6.1** — Viết tài liệu kiến trúc tổng thể
  - File: `ARCHITECTURE.md` (v4.1)
  - Nội dung: Mục tiêu, nguyên lý, kiến trúc tổng thể, phân vai agent, workflow, governance, tech stack, 7 quality checks
- [x] **0.6.2** — Vẽ sơ đồ hệ thống
  - System architecture diagram (User → FastAPI → Execution → Verification)
  - Hybrid execution diagram (Dev mode vs Prod mode)
  - Dual-model validation gate diagram
- [x] **0.6.3** — Viết spec YAML cho từng agent
  - 7 agent specs trong `/specs/`: gatekeeper, orchestrator, specialist, auditor, mentor, devops, monitoring
  - OpenCode integration spec: `opencode_integration.yaml` (v3, renamed from opencode_adapter)
- [x] **0.6.4** — Tài liệu hóa model responsibilities
  - File: `/shared/config/models.yaml` (v4)
  - Bảng mapping: Agent → Model → Lý do → Use case
- [x] **0.6.5** — Tạo file `README.md` cho repo
  - Tổng quan dự án, cách setup, cách chạy, cấu trúc thư mục
- [x] **0.6.6** — Viết 16+ design docs
  - `docs/state-machine.md` — Workflow state machine
  - `docs/agent-matrix.md` — Agent responsibility matrix
  - `docs/dynamic-model-router.md` — v4.1: Dynamic Model Router + Validation Gate
  - `docs/opencode-architecture.md` — OpenCode integration design
  - `docs/security-design.md` — Auth, RBAC, API security
  - `docs/error-handling-resilience.md` — Circuit breaker, retry, fallback
  - `docs/llm-integration.md` — LLM call management
  - `docs/database-migration.md` — Alembic migration strategy
  - `docs/api-specification.md` — REST API design
  - `docs/testing-strategy.md` — Testing approach
  - `docs/non-functional-requirements.md` — NFRs
  - `docs/mvp-scope.md` — Trimmed MVP definition
  - `docs/llm-observability.md` — LLM metrics, cost tracking
  - `docs/risk-assessment.md` — Risks and mitigations
  - `docs/data-flow.md` — Data flow diagrams
  - `docs/architecture-change-log.md` — v2 → v3 change log

### Output
- `ARCHITECTURE.md` (v4.1)
- `README.md` (v4.1)
- 7 agent specs + 1 OpenCode integration spec
- 16+ design docs
- `shared/config/models.yaml` (v4)
- `shared/config/model_capabilities.yaml`
- `shared/config/model_router.py`

---

## Checklist Phase 0

| # | Task | Status | Notes |
|---|---|---|---|
| 0.1 | Architectural Laws | ✅ | 20 rules (4 critical, 8 high, 8 medium) |
| 0.2 | Workflow State Machine | ✅ | 11 states, 3 terminal, 22 valid transitions, v3 validation gatecheck |
| 0.3 | Agent Responsibility Matrix | ✅ | 8 agents (7 + Validator v4.1), FastAPI-centric |
| 0.4 | Dynamic Model Router | ✅ | v4: 5 models, scoring algorithm, self-awareness, fallback chains |
| 0.5 | Database Schema Draft | ✅ | 15+ tables, junction tables, pgvector, views, triggers, v2.0.0 |
| 0.6 | Documentation | ✅ | 16+ docs, ARCHITECTURE.md v4.1, README.md v4.1 |
| 0.7 | OpenCode Integration Spec | ✅ | Renamed opencode_adapter → opencode_integration.yaml (v3) |

**Definition of Done cho Phase 0:**
- [x] Có file laws.yaml hoàn chỉnh (20 laws)
- [x] Có state machine (11 states, 22 transitions, validation gatecheck v3)
- [x] Có agent matrix (8 agents: 7 + Validator v4.1)
- [x] Có Dynamic Model Router (v4: 5 models, scoring, fallback)
- [x] Có database schema (15+ tables, junction tables, pgvector, v2.0.0)
- [x] Có tài liệu kiến trúc tổng thể (v4.1)
- [x] Có OpenCode integration spec (v3)
- [x] Có models.yaml v4 (5 models, circuit breaker, mentor quota)
- [x] Có architecture-change-log.md (v2 → v3)
- [x] Có 16+ design docs

**Version history:**
- v1: Initial design (9 states, 12 laws, 4 agents)
- v2: Added FAILED/CANCELLED states, junction tables, auth (11 states, 20 laws)
- v3: FastAPI = brain, OpenCode = integration (hybrid architecture)
- v4: Dynamic Model Router replaces fixed agent-model mapping (5 models: DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus, MiniMax M2.7)
- v4.1: Dual-Model Validation Gate — cross-validation before NEW → ANALYZING (Gatekeeper + Validator)
