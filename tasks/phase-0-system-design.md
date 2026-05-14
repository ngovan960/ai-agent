# PHASE 0 — SYSTEM DESIGN (1–2 tuần)

## Mục tiêu
Xác định toàn bộ nền tảng kiến trúc trước khi code:
- Luật hệ thống (Architectural Laws)
- Workflow state machine
- Agent responsibility matrix
- Database schema draft
- Model responsibilities
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
  - Check rule: Mọi endpoint phải có validation layer (Pydantic/Zod)
- [x] **0.1.4** — Định nghĩa LAW-003: No direct DB access from UI
  - Severity: high
  - Check rule: UI chỉ gọi API, không có connection string hoặc query trực tiếp
- [x] **0.1.5** — Định nghĩa LAW-004: Critical actions require human approval
  - Severity: critical
  - Check rule: Deploy production, delete data, thay đổi schema phải có approval
- [x] **0.1.6** — Bổ sung luật bổ sung tùy nghiệp vụ
  - LAW-005: No hardcoded secrets
  - LAW-006: All errors must be logged
  - LAW-007: API response time < 3s
  - LAW-008: No agent modifies architecture without approval
  - LAW-009: No DONE status without verification
  - LAW-010: No infinite retry loops
  - LAW-011: Scope adherence required
  - LAW-012: All state changes must be audited

### Output
- File `laws.yaml` hoàn chỉnh với tối thiểu 7 rules

---

## 0.2. Workflow State Machine

### Mô tả
Thiết kế state machine định nghĩa luồng đi của mọi task trong hệ thống.

### Tasks
- [x] **0.2.1** — Thiết kế state machine diagram
  - States: NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
  - Vẽ bằng Mermaid hoặc Excalidraw
- [x] **0.2.2** — Định nghĩa rules cho từng state transition
  - NEW → ANALYZING: Gatekeeper đã phân loại
  - ANALYZING → PLANNING: Orchestrator đã chia task
  - PLANNING → IMPLEMENTING: Agent đã nhận task
  - IMPLEMENTING → VERIFYING: Code đã hoàn thành
  - VERIFYING → REVIEWING: Sandbox đã pass
  - REVIEWING → DONE: Auditor đã approve
- [x] **0.2.3** — Xác định các transition không hợp lệ
  - DONE → IMPLEMENTING: Không cho phép (phải qua rollback)
  - VERIFYING → PLANNING: Không cho phép (phải qua retry/escalate)
  - REVIEWING → IMPLEMENTING: Không cho phép (phải qua retry)
- [x] **0.2.4** — Định nghĩa các transition đặc biệt
  - Bất kỳ state → ESCALATED: Khi retry > 2
  - Bất kỳ state → BLOCKED: Khi có dependency chưa xong
  - ESCALATED → PLANNING: Mentor đã takeover
  - BLOCKED → PLANNING: Dependency đã xong

### Output
- File `state-machine.md` hoặc `state-machine.mermaid`
- Bảng transition rules

---

## 0.3. Agent Responsibility Matrix

### Mô tả
Định nghĩa rõ vai trò, trách nhiệm và model AI phù hợp cho từng agent.

### Tasks
- [x] **0.3.1** — Gatekeeper Agent
  - Trách nhiệm: Routing, phân loại task, tra cứu cache/memory, kiểm tra task cũ
  - Model: DeepSeek V4 Flash (nhanh, rẻ)
  - Input: User request
  - Output: Task classification (easy/medium/hard)
- [x] **0.3.2** — Orchestrator Agent
  - Trách nhiệm: Hiểu trạng thái dự án, chia task, chọn agent, điều phối workflow, quyết định review/retry/escalate/takeover
  - Model: Qwen 3.5 Plus hoặc Qwen 3.6 Plus (reasoning tốt)
  - Input: Classified task
  - Output: Task breakdown + assignment plan
- [x] **0.3.3** — Specialist Agent
  - Trách nhiệm: Viết code, thiết kế module, xử lý logic, algorithm, build feature
  - Model: DeepSeek V4 Pro (mạnh về code)
  - Input: Task spec
  - Output: Code + tests
- [x] **0.3.4** — Auditor Agent
  - Trách nhiệm: So code với spec, kiểm tra cấu trúc, kiến trúc, clean code, compliance với law
  - Model: Qwen 3.5 Plus
  - Input: Code + spec + laws
  - Output: APPROVED / REVISE / ESCALATE
- [x] **0.3.5** — Supreme Mentor Agent
  - Trách nhiệm: Xử lý deadlock, quyết định chiến lược, giải quyết mâu thuẫn, refactor workflow, final verdict
  - Model: Qwen 3.6 Plus (mạnh nhất)
  - Trigger: Khi task fail > 2 lần hoặc hệ thống bế tắc
  - Output: Final decision + lesson learned
- [x] **0.3.6** — DevOps/Deployment Agent
  - Trách nhiệm: Build image, chạy Docker, deploy staging, quản lý CI/CD, theo dõi logs, rollback
  - Model: DeepSeek V4 Pro hoặc Flash tùy task
  - Input: Verified code
  - Output: Deployed service
- [x] **0.3.7** — Monitoring/Maintenance Agent
  - Trách nhiệm: Theo dõi lỗi, phát hiện anomaly, cảnh báo regressions, gom feedback, hỗ trợ cải tiến
  - Model: DeepSeek Flash, GLM, hoặc Qwen tùy ngữ cảnh
  - Input: Logs + metrics
  - Output: Alert + bug report

### Output
- File `agent-matrix.md` với bảng tổng hợp 7 agents

---

## 0.4. Database Schema Draft

### Mô tả
Thiết kế schema PostgreSQL cho toàn bộ hệ thống.

### Tasks
- [x] **0.4.1** — Schema: projects
  - Fields: id (UUID), name, description, status, tech_stack, architecture, created_at, updated_at
  - Relations: 1 project → many modules, many tasks
- [x] **0.4.2** — Schema: modules
  - Fields: id (UUID), project_id (FK), name, description, status, dependencies (array), created_at, updated_at
  - Relations: 1 module → many tasks
- [x] **0.4.3** — Schema: tasks
  - Fields: id (UUID), project_id (FK), module_id (FK), title, description, owner (agent_name), priority, status, confidence (float), retries (int), dependencies (array), outputs (JSON), created_at, updated_at, completed_at
  - Relations: 1 task → many retries, many audit_logs
- [x] **0.4.4** — Schema: retries
  - Fields: id (UUID), task_id (FK), attempt_number, reason, agent_name, output, created_at
  - Relations: 1 retry → 1 task
- [x] **0.4.5** — Schema: audit_logs
  - Fields: id (UUID), task_id (FK), action, actor (agent_name), input, output, result, created_at
  - Relations: 1 audit_log → 1 task
- [x] **0.4.6** — Schema: mentor_instructions
  - Fields: id (UUID), task_id (FK), instruction_type, content, context, applied (bool), created_at
  - Relations: 1 instruction → 1 task
- [x] **0.4.7** — Schema: decisions
  - Fields: id (UUID), project_id (FK), decision, reason, context, created_at
  - Relations: 1 decision → 1 project
- [x] **0.4.8** — Vẽ ERD diagram
  - Dùng dbdiagram.io hoặc Mermaid
- [x] **0.4.9** — Review và hoàn thiện schema
  - Kiểm tra foreign keys, indexes, constraints
  - Thêm indexes cho fields hay query: status, project_id, task_id
  - Bổ sung: workflows, deployments, cost_tracking tables
  - Thêm updated_at triggers

### Output
- File `schema.sql` hoặc `schema.md`
- ERD diagram

---

## 0.5. Documentation

### Mô tả
Viết tài liệu kiến trúc tổng thể để làm reference cho toàn bộ team/dev.

### Tasks
- [x] **0.5.1** — Viết tài liệu kiến trúc tổng thể
  - File: `ARCHITECTURE.md`
  - Nội dung: Mục tiêu, nguyên lý, kiến trúc tổng thể, phân vai agent, workflow, governance, tech stack
  - Bổ sung: Hybrid architecture section, OpenCode adapter section
- [x] **0.5.2** — Vẽ sơ đồ hệ thống
  - System architecture diagram (User → Core Orchestration → Execution Layer → Verification)
  - Hybrid execution diagram (Dev mode vs Prod mode)
  - Dùng Mermaid hoặc Excalidraw
- [x] **0.5.3** — Viết spec YAML/JSON cho từng component
  - File: `/specs/gatekeeper.yaml`
  - File: `/specs/orchestrator.yaml`
  - File: `/specs/specialist.yaml`
  - File: `/specs/auditor.yaml`
  - File: `/specs/mentor.yaml`
  - File: `/specs/devops.yaml`
  - File: `/specs/monitoring.yaml`
  - File: `/specs/opencode_adapter.yaml` (MỚI)
- [x] **0.5.4** — Tài liệu hóa model responsibilities
  - Bảng mapping: Agent → Model → Lý do → Use case
  - File: `/shared/config/models.yaml`
- [x] **0.5.5** — Tạo file `README.md` cho repo
  - Tổng quan dự án, cách setup, cách chạy, cấu trúc thư mục
  - Bổ sung: Hybrid architecture explanation

### Output
- `ARCHITECTURE.md`
- `README.md`
- `/specs/*.yaml`
- System diagram

---

## Checklist Phase 0

| # | Task | Status | Notes |
|---|---|---|---|
| 0.1 | Architectural Laws | ✅ | 20 rules (v3), file: governance/laws.yaml |
| 0.2 | Workflow State Machine | ✅ | 11 states, 3 terminal, 22 valid transitions |
| 0.3 | Agent Responsibility Matrix | ✅ | 7 agents, FastAPI-centric (v3) |
| 0.4 | Database Schema Draft | ✅ | 15+ tables, junction tables, pgvector, v2.0.0 |
| 0.5 | Documentation | ✅ | 16+ docs, ARCHITECTURE.md v3, README.md v3 |
| 0.6 | Dynamic Model Router | ✅ | NEW v4: model_capabilities.yaml, model_router.py, 5 models |
| 0.7 | OpenCode Integration Spec | ✅ | Renamed opencode_adapter → opencode_integration.yaml (v3) |

**Definition of Done cho Phase 0:**
- [x] Có file laws.yaml hoàn chỉnh (20 laws)
- [x] Có state machine diagram (11 states, 22 transitions)
- [x] Có agent matrix (7 agents, FastAPI-centric)
- [x] Có database schema (15+ tables, v2.0.0)
- [x] Có tài liệu kiến trúc tổng thể (v3)
- [x] Có OpenCode integration spec (v3)
- [x] Có Dynamic Model Router (v4): model_capabilities.yaml, model_router.py
- [x] Có models.yaml v4 (5 models, circuit breaker, mentor quota)
- [x] Có architecture-change-log.md (v2 → v3)

**Version history:**
- v1: Initial design (9 states, 12 laws, 4 agents)
- v2: Added FAILED/CANCELLED states, junction tables, auth (11 states, 20 laws)
- v3: FastAPI = brain, OpenCode = integration (hybrid architecture)
- v4: Dynamic Model Router replaces fixed agent-model mapping (5 models retained)
