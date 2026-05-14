# Agent Responsibility Matrix - AI SDLC System

## Overview
This document defines all agents in the system, their responsibilities, assigned AI models, inputs, outputs, and escalation paths. OpenCode serves as the brain coordinating all agent calls.

## OpenCode as the Brain
OpenCode is the central orchestrator that:
1. Receives user requests
2. Dispatches tasks to appropriate agents
3. Builds context for each agent call
4. Manages state transitions
5. Handles errors, retries, and escalation
6. Executes code changes via built-in tools (bash, edit, write, read, glob, grep)

All agent calls go through OpenCode's LLM Gateway (with circuit breaker, retry, cost tracking).

## Agent Summary Table

| Agent | Role | Model | OpenCode Tools | Trigger | Output |
|---|---|---|---|---|---|
| Gatekeeper | Routing & Classification | DeepSeek V4 Flash | read, glob, grep | User request | Task classification |
| Orchestrator | Workflow Coordination | Qwen 3.6 Plus | read, glob, grep | Classified task | Task breakdown + plan |
| Specialist | Code Execution | DeepSeek V4 Pro | bash, edit, write, read, glob, grep | Task assignment | Code + tests + docs |
| Auditor | Quality Review | Qwen 3.5 Plus | bash (tests), read, glob, grep | Verified code | APPROVED/REVISE/ESCALATE |
| Mentor | Strategic Decision | Qwen 3.6 Plus | read, glob, grep | Escalation | Final verdict |
| DevOps | Deployment | DeepSeek V4 Pro | bash, read | Verified code | Deployed service |
| Monitoring | Observability | DeepSeek V4 Flash | bash, read | Continuous | Alerts + reports |

---

## 1. Gatekeeper Agent

### Role
Cổng đầu vào của hệ thống. Nhận yêu cầu từ user, phân loại, tra cứu memory, quyết định routing.

### Assigned Model
- **Primary**: DeepSeek V4 Flash
- **Fallback**: DeepSeek V4 Pro
- **Reason**: Nhanh, rẻ, phù hợp cho phân loại và tra cứu đơn giản

### OpenCode Tools
- **read**: Đọc file, task specs, memory
- **glob**: Tìm file liên quan
- **grep**: Tìm patterns trong codebase

### Responsibilities
1. Nhận yêu cầu từ user (natural language)
2. Kiểm tra task đã từng làm chưa (tra cứu cache/memory)
3. Phân loại task theo mức độ khó (complexity scoring 1-10)
4. Quyết định xử lý cục bộ hay escalate
5. Tạo task record với status = NEW

### Input
- User request (natural language)
- Memory lookup results (past similar tasks)

### Output
- Parsed request (intent, entities, constraints)
- Complexity score (1-10)
- Routing decision (easy/medium/hard)
- Task record (NEW status)

### Rules
- Không được tự ý bỏ qua memory lookup
- Phải phân loại complexity trước khi routing
- Nếu tìm thấy task tương tự trong memory → return cached solution

### Escalation
- Nếu không thể phân loại → escalate đến Orchestrator

---

## 2. Orchestrator Agent

### Role
Bộ não điều phối toàn hệ thống. Hiểu trạng thái dự án, chia task, chọn agent, điều phối workflow.

### Assigned Model
- **Primary**: Qwen 3.6 Plus
- **Fallback**: Qwen 3.5 Plus
- **Reason**: Reasoning tốt, tổ chức workflow tốt, phù hợp vai trò quản trị

### OpenCode Tools
- **read**: Đọc project state, task specs, memory
- **glob**: Tìm related files
- **grep**: Tìm patterns

### Responsibilities
1. Hiểu trạng thái dự án (modules, tasks, dependencies, blockers)
2. Chia task thành các bước nhỏ (task breakdown)
3. Xác định dependencies giữa subtasks
4. Chọn agent phù hợp cho từng bước
5. Điều phối luồng làm việc
6. Quyết định khi nào cần review, retry, escalate hoặc takeover

### Input
- Classified task (từ Gatekeeper)
- Project state (modules, tasks, dependencies)
- Memory results (past solutions, lessons learned)

### Output
- Task breakdown list (subtasks với description, expected_output)
- Dependency graph
- Agent assignment plan
- Workflow execution order

### Rules
- Không được chia task quá nhỏ (min scope per task)
- Phải xác định dependencies trước khi assign
- Phải chọn agent phù hợp với complexity
- Không được bỏ qua memory lookup

### Escalation
- Nếu không thể chia task → escalate đến Mentor

---

## 3. Specialist Agent

### Role
Nhóm agent thực thi chính. Viết code, thiết kế module, xử lý logic, algorithm, build feature.

### Assigned Model
- **Primary**: DeepSeek V4 Pro
- **Fallback**: Qwen 3.5 Plus
- **Reason**: Mạnh về code, mạnh về logic thực thi, phù hợp làm developer chính

### OpenCode Tools
- **bash**: Chạy tests, lint, build commands
- **edit**: Sửa code hiện có
- **write**: Tạo file mới
- **read**: Đọc code, specs, context
- **glob**: Tìm file
- **grep**: Tìm patterns

### Responsibilities
1. Viết code theo task spec
2. Thiết kế module structure
3. Xử lý logic phức tạp
4. Xử lý algorithm
5. Build feature hoàn chỉnh (code + tests + docs)

### Input
- Task spec (title, description, expected_output)
- Context (related modules, memory, architectural laws)
- Agent assignment (từ Orchestrator)

### Output
- Code files
- Test files
- Documentation (if required)

### Rules
- **Chỉ làm đúng scope** — không tự ý thêm feature ngoài task
- **Không tự ý đổi kiến trúc** — phải tuân thủ architectural laws
- **Nếu thiếu thông tin** → hỏi theo format ngắn gọn
- **Nếu task quá khó** → đánh dấu #ESCALATE
- **Không được bỏ qua tests** — phải viết tests cho code
- **OpenCode thực thi code changes** — Specialist output directions, OpenCode executes

### Escalation
- Nếu task vượt quá capability → đánh dấu #ESCALATE
- Nếu retry > 2 → auto-escalate đến Mentor

---

## 4. Auditor Agent

### Role
Bộ phận kiểm định độc lập. So code với spec, kiểm tra cấu trúc, kiến trúc, clean code, compliance.

### Assigned Model
- **Primary**: Qwen 3.5 Plus
- **Fallback**: Qwen 3.6 Plus
- **Reason**: Reasoning tốt, phù hợp cho review và phân tích

### OpenCode Tools
- **bash**: Chỉ chạy tests, lint (không sửa code)
- **read**: Đọc code, specs, laws
- **glob**: Tìm file
- **grep**: Tìm patterns, violations

### Responsibilities
1. So code với spec (đúng yêu cầu chưa)
2. Kiểm tra cấu trúc (file structure, naming conventions)
3. Kiểm tra kiến trúc (layer separation, dependency direction)
4. Kiểm tra clean code (DRY, SOLID, readability)
5. Kiểm tra compliance với architectural laws
6. Kiểm tra quality trước khi chuyển trạng thái DONE

### Input
- Code (từ Specialist)
- Spec (expected_output từ task)
- Test results (từ Sandbox)
- Architectural laws (từ laws.yaml)

### Output
- Verdict: **APPROVED** / **REVISE** / **ESCALATE**
- Scores: spec_match, structure, architecture, clean_code, law_compliance
- Violations list (nếu có)
- Suggestions (nếu REVISE)

### Rules
- Phải kiểm tra tất cả 5 aspects trước khi đưa ra verdict
- Verdict dựa trên confidence score:
  - >= 80% → APPROVED
  - 60-80% → REVISE
  - < 60% → ESCALATE
- Không được approve nếu có critical law violation

### Escalation
- Nếu phát hiện critical law violation → ESCALATE
- Nếu không thể xác định quality → ESCALATE

---

## 5. Supreme Mentor Agent

### Role
Cấp cao nhất, chỉ xuất hiện khi hệ thống bế tắc hoặc task quá khó. Xử lý deadlock, đưa ra quyết định chiến lược.

### Assigned Model
- **Primary**: Qwen 3.6 Plus
- **Reason**: Model mạnh nhất, reasoning tốt nhất, phù hợp cho quyết định chiến lược

### OpenCode Tools
- **read**: Đọc task history, code, audit logs
- **glob**: Tìm related files
- **grep**: Tìm patterns

### Quota
- **Max 10 calls per day** (enforced via mentor_quota table)
- If exceeded → reject with clear error message

### Responsibilities
1. Xử lý deadlock (circular dependency, retry loop)
2. Đưa ra quyết định chiến lược (spec vs code vs review conflict)
3. Giải quyết mâu thuẫn giữa spec, code và review
4. Refactor workflow nếu cần
5. Đưa ra final verdict

### Input
- Task history (all retries, audits, logs)
- Conflict details (spec, code, review results)
- Memory (past decisions, lessons learned)

### Output
- Final verdict: **APPROVED** / **REJECT** / **MODIFY**
- Resolution plan (nếu MODIFY)
- Lesson learned (lưu vào memory)

### Rules
- Chỉ được kích hoạt khi task bị escalate
- Quyết định của Mentor là **final** — không được retry sau Mentor verdict
- Phải lưu lesson learned sau mỗi decision
- Có giới hạn quota (max 10 calls/day, enforced by database)

### ESCALATED → DONE Exception
- Mentor có thể approve ESCALATED → DONE **CHỈ KHI** task đã có verification pass record
- Nếu chưa verify → Mentor phải chuyển về PLANNING để làm lại từ đầu
- Mentor phải cite verification evidence trong audit log

### Escalation
- Mentor là cấp cao nhất — không có escalation từ Mentor
- Nếu Mentor không thể giải quyết → require human intervention

---

## 6. DevOps / Deployment Agent

### Role
Phụ trách build, deploy, CI/CD, monitoring logs, rollback.

### Assigned Model
- **Primary**: DeepSeek V4 Pro (cho complex deployment)
- **Fallback**: DeepSeek V4 Flash (cho simple deployment)

### OpenCode Tools
- **bash**: Chạy build, deploy, health check commands
- **read**: Đọc build logs, deployment configs

### Responsibilities
1. Build Docker image từ verified code
2. Deploy staging environment
3. Quản lý CI/CD pipeline
4. Theo dõi logs từ containers
5. Rollback nếu deployment fail

### Rules
- Không được deploy production nếu chưa có human approval (LAW-004)
- Phải verify staging sau khi deploy
- Phải log mọi deployment action
- Phải có rollback plan trước khi deploy

### Escalation
- Nếu deployment fail → auto-rollback + notify
- Nếu rollback fail → escalate đến Mentor

---

## 7. Monitoring / Maintenance Agent

### Role
Theo dõi lỗi, phát hiện anomaly, cảnh báo regressions, gom feedback thành bug report.

### Assigned Model
- **Primary**: DeepSeek V4 Flash (cho monitoring liên tục)
- **Fallback**: DeepSeek V4 Pro (cho complex analysis)
- **Reason**: Rẻ, nhanh, phù hợp cho monitoring liên tục

### OpenCode Tools
- **bash**: Chạy health checks, query metrics
- **read**: Đọc logs, metrics

### Responsibilities
1. Theo dõi lỗi (error tracking, grouping)
2. Phát hiện anomaly (spike in errors, latency)
3. Cảnh báo regressions (so với baseline)
4. Gom feedback thành bug report
5. Hỗ trợ cải tiến hệ thống

### Rules
- Phải monitor liên tục (24/7)
- Phải alert ngay khi phát hiện critical issue
- Phải gom feedback thành bug report có cấu trúc
- Phải đề xuất improvement dựa trên trends

### Escalation
- Nếu phát hiện critical issue → alert + escalate
- Nếu không thể xác định root cause → escalate đến Specialist

---

## Model Assignment Summary

```yaml
model_assignments:
  deepseek_v4_flash:
    agents: [Gatekeeper, Monitoring]
    use_case: "Phân loại, tra cứu, monitoring liên tục"
    cost: low
    speed: fast
    tools: read, glob, grep (Gatekeeper); bash, read (Monitoring)

  deepseek_v4_pro:
    agents: [Specialist, DevOps]
    use_case: "Viết code, deployment automation"
    cost: medium
    speed: medium
    tools: bash, edit, write, read, glob, grep (Specialist); bash, read (DevOps)

  qwen_3_5_plus:
    agents: [Auditor]
    use_case: "Review, kiểm định, phân tích"
    cost: medium
    speed: medium
    tools: bash (tests only), read, glob, grep

  qwen_3_6_plus:
    agents: [Orchestrator, Mentor]
    use_case: "Điều phối, quyết định chiến lược"
    cost: high
    speed: slow
    tools: read, glob, grep
```

## Escalation Path

```
User → OpenCode → Gatekeeper → Orchestrator → Specialist → Sandbox → Auditor → DONE
                                       ↓                       ↓
                                   Mentor ←←←←←←←←←←←←←←←←←← (escalate)
                                       ↓
                                   Human (nếu Mentor không giải quyết được)
```

## Terminal States

| State | Description | How to Reach |
|---|---|---|
| DONE | Task completed successfully | Auditor approves, or Mentor approves with verified output |
| FAILED | Task permanently failed | Mentor rejects, fatal error, verification critically fails |
| CANCELLED | Task cancelled by user | User decides to cancel at any non-terminal state |

## Metadata
- **Version**: 2.0.0
- **Created**: 2026-05-14
- **Last Updated**: 2026-05-14
- **Total Agents**: 7
- **Total Models**: 4