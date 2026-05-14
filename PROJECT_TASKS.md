# HỆ THỐNG ĐIỀU PHỐI AI SDLC - PROJECT TASKS
## AI Software Company Operating System

---

# PHASE 0 — SYSTEM DESIGN (1–2 tuần)

## 0.1. Architectural Laws
- [ ] Tạo file `laws.yaml` / `laws.json` định nghĩa luật hệ thống
- [ ] Định nghĩa rule: No business logic in controller (LAW-001)
- [ ] Định nghĩa rule: All APIs must validate input (LAW-002)
- [ ] Định nghĩa rule: No direct DB access from UI (LAW-003)
- [ ] Định nghĩa rule: Critical actions require human approval (LAW-004)
- [ ] Bổ sung các luật bổ sung tùy nghiệp vụ

## 0.2. Workflow State Machine
- [ ] Thiết kế state machine: NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE
- [ ] Định nghĩa rules cho từng state transition
- [ ] Xác định các transition không hợp lệ (ví dụ: DONE → IMPLEMENTING không có rollback)
- [ ] Vẽ diagram state machine (Mermaid/Excalidraw)

## 0.3. Agent Responsibility Matrix
- [ ] Định nghĩa vai trò Gatekeeper Agent: Routing, phân loại task
- [ ] Định nghĩa vai trò Orchestrator Agent: Điều phối, chia task, ra quyết định
- [ ] Định nghĩa vai trò Specialist Agent: Viết code, thực thi task
- [ ] Định nghĩa vai trò Auditor Agent: Review, kiểm định độc lập
- [ ] Định nghĩa vai trò Supreme Mentor: Xử lý deadlock, quyết định chiến lược
- [ ] Định nghĩa vai trò DevOps/Deployment Agent: Build, deploy, CI/CD
- [ ] Định nghĩa vai trò Monitoring/Maintenance Agent: Theo dõi, alert, rollback
- [ ] Gán model AI phù hợp cho từng agent

## 0.4. Database Schema Draft
- [ ] Thiết kế schema: projects
- [ ] Thiết kế schema: tasks
- [ ] Thiết kế schema: modules
- [ ] Thiết kế schema: retries
- [ ] Thiết kế schema: audit_logs
- [ ] Thiết kế schema: mentor_instructions
- [ ] Review và hoàn thiện toàn bộ schema

## 0.5. Documentation
- [ ] Viết tài liệu kiến trúc tổng thể (Markdown)
- [ ] Vẽ sơ đồ hệ thống (Mermaid/Excalidraw)
- [ ] Viết spec YAML/JSON cho từng component
- [ ] Tài liệu hóa model responsibilities

---

# PHASE 1 — CORE STATE SYSTEM (2–3 tuần)

## 1.1. Setup Project
- [ ] Tạo monorepo structure: /apps, /services, /agents, /governance, /memory, /dashboard
- [ ] Setup Python/FastAPI project
- [ ] Setup PostgreSQL database
- [ ] Setup SQLAlchemy ORM
- [ ] Setup Pydantic validation
- [ ] Setup Redis (cache, queue)
- [ ] Cấu hình môi trường dev (docker-compose)

## 1.2. Project Registry
- [ ] Tạo model Project (SQLAlchemy)
- [ ] Tạo Pydantic schema cho Project
- [ ] Build API: GET /projects
- [ ] Build API: POST /projects
- [ ] Build API: GET /projects/{project_id}
- [ ] Build API: PUT /projects/{project_id}
- [ ] Build API: DELETE /projects/{project_id}
- [ ] Unit test cho Project Registry

## 1.3. Module Registry
- [ ] Tạo model Module (SQLAlchemy)
- [ ] Tạo Pydantic schema cho Module
- [ ] Build API: GET /modules
- [ ] Build API: POST /modules
- [ ] Build API: GET /modules/{module_id}
- [ ] Build API: PUT /modules/{module_id} (update status)
- [ ] Build API: GET /projects/{project_id}/modules
- [ ] Unit test cho Module Registry

## 1.4. Task Registry
- [ ] Tạo model Task (SQLAlchemy) với fields: id, title, description, owner, priority, status, confidence, retries, dependencies, outputs, timestamps
- [ ] Tạo Pydantic schema cho Task
- [ ] Build API: GET /tasks
- [ ] Build API: POST /tasks
- [ ] Build API: GET /tasks/{task_id}
- [ ] Build API: PUT /tasks/{task_id}
- [ ] Build API: GET /projects/{project_id}/tasks
- [ ] Build API: GET /modules/{module_id}/tasks
- [ ] Unit test cho Task Registry

## 1.5. State Transition Engine
- [ ] Implement state machine logic (NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE)
- [ ] Validate state transitions (chặn transition không hợp lệ)
- [ ] Build API: POST /tasks/{task_id}/transition
- [ ] Implement event logging cho mỗi transition
- [ ] Unit test cho state transitions

## 1.6. Retry Tracking
- [ ] Tạo model Retry (SQLAlchemy)
- [ ] Implement retry counter per task
- [ ] Implement retry limit check (max 2 retries)
- [ ] Build API: POST /tasks/{task_id}/retry
- [ ] Build API: GET /tasks/{task_id}/retries
- [ ] Unit test cho retry tracking

## 1.7. Audit Logs (Cơ bản)
- [ ] Tạo model AuditLog (SQLAlchemy)
- [ ] Implement audit log middleware
- [ ] Log mọi action: ai làm gì, khi nào, output, lý do fail, ai approve
- [ ] Build API: GET /audit-logs
- [ ] Build API: GET /audit-logs/{task_id}
- [ ] Unit test cho audit logs

## 1.8. Integration Tests
- [ ] Test end-to-end: tạo project → tạo module → tạo task → transition states
- [ ] Test retry flow
- [ ] Test audit logging

---

# PHASE 2 — WORKFLOW ENGINE (2–3 tuần)

## 2.1. LangGraph Setup
- [ ] Cài đặt LangGraph
- [ ] Thiết kế workflow graph cơ bản: receive task → plan → assign → execute → verify → review → done
- [ ] Implement LangGraph nodes cho từng bước
- [ ] Implement LangGraph edges (conditional routing)
- [ ] Test workflow graph cơ bản

## 2.2. Workflow Nodes Implementation
- [ ] Implement node: Receive Task (Intake)
- [ ] Implement node: Plan (chia task, xác định dependency)
- [ ] Implement node: Assign (giao task cho agent phù hợp)
- [ ] Implement node: Execute (gọi agent thực thi)
- [ ] Implement node: Verify (chạy sandbox)
- [ ] Implement node: Review (Auditor kiểm tra)
- [ ] Implement node: Done (cập nhật state)

## 2.3. Dependency Management
- [ ] Implement dependency graph cho tasks
- [ ] Build logic: task B chỉ chạy khi task A hoàn thành
- [ ] Build API: GET /tasks/{task_id}/dependencies
- [ ] Build API: POST /tasks/{task_id}/dependencies
- [ ] Implement circular dependency detection
- [ ] Unit test cho dependency management

## 2.4. Escalation Engine
- [ ] Implement escalation logic: retry > 2 → ESCALATE
- [ ] Build API: POST /tasks/{task_id}/escalate
- [ ] Implement notification khi escalate
- [ ] Implement escalation routing (chuyển lên Mentor)
- [ ] Unit test cho escalation engine

## 2.5. Takeover Mode
- [ ] Implement Mentor takeover logic
- [ ] Implement Mentor rewrite capability
- [ ] Implement Mentor redesign capability
- [ ] Implement Mentor override execution
- [ ] Build API: POST /tasks/{task_id}/takeover
- [ ] Unit test cho takeover mode

## 2.6. Workflow Orchestration
- [ ] Kết nối toàn bộ nodes thành workflow hoàn chỉnh
- [ ] Implement error handling trong workflow
- [ ] Implement timeout handling
- [ ] Implement workflow recovery (resume sau lỗi)
- [ ] Integration test: end-to-end workflow

## 2.7. Gatekeeper Agent
- [ ] Implement Gatekeeper: nhận yêu cầu từ user
- [ ] Implement Gatekeeper: kiểm tra task đã từng làm chưa (tra cứu cache/memory)
- [ ] Implement Gatekeeper: phân loại task theo độ khó
- [ ] Implement Gatekeeper: quyết định xử lý cục bộ hay escalate
- [ ] Tích hợp Gatekeeper vào workflow (node đầu tiên)
- [ ] Unit test cho Gatekeeper

## 2.8. Orchestrator Agent
- [ ] Implement Orchestrator: hiểu trạng thái dự án
- [ ] Implement Orchestrator: chia task thành các bước nhỏ
- [ ] Implement Orchestrator: chọn agent phù hợp cho từng bước
- [ ] Implement Orchestrator: điều phối luồng làm việc
- [ ] Implement Orchestrator: quyết định review, retry, escalate, takeover
- [ ] Tích hợp Orchestrator vào workflow
- [ ] Unit test cho Orchestrator

---

# PHASE 3 — AGENT RUNTIME (2–4 tuần)

## 3.1. Model Router
- [ ] Implement complexity scoring cho task
- [ ] Implement routing logic: complexity < 3 → Flash, < 7 → Pro, >= 7 → Qwen
- [ ] Implement model selection API
- [ ] Implement fallback mechanism (model lỗi → chuyển sang model khác)
- [ ] Unit test cho model router

## 3.2. Agent Runtime Core
- [ ] Implement execute_agent() function
- [ ] Implement retry_agent() function
- [ ] Implement escalate_agent() function
- [ ] Implement takeover() function
- [ ] Implement agent context management
- [ ] Unit test cho agent runtime

## 3.3. Prompt Templates
- [ ] Tạo planner prompt template
- [ ] Tạo coder prompt template
- [ ] Tạo reviewer prompt template
- [ ] Tạo mentor prompt template
- [ ] Tạo gatekeeper prompt template
- [ ] Tạo orchestrator prompt template
- [ ] Quản lý prompt templates trong file config
- [ ] Unit test cho prompt rendering

## 3.4. Context Builder
- [ ] Implement context builder: chỉ load task hiện tại
- [ ] Implement context builder: load related modules
- [ ] Implement context builder: load relevant memory
- [ ] Implement context size limit (không load toàn bộ project)
- [ ] Unit test cho context builder

## 3.5. Specialist Agent
- [ ] Implement Specialist: viết code theo task
- [ ] Implement Specialist: thiết kế module
- [ ] Implement Specialist: xử lý logic phức tạp
- [ ] Implement Specialist: xử lý algorithm
- [ ] Implement Specialist: build feature
- [ ] Implement rule: chỉ làm đúng scope, không tự ý đổi kiến trúc
- [ ] Implement rule: nếu thiếu thông tin thì hỏi theo format ngắn gọn
- [ ] Implement rule: nếu task quá khó thì đánh dấu #ESCALATE
- [ ] Unit test cho Specialist Agent

## 3.6. Auditor Agent
- [ ] Implement Auditor: so code với spec
- [ ] Implement Auditor: kiểm tra cấu trúc
- [ ] Implement Auditor: kiểm tra kiến trúc
- [ ] Implement Auditor: kiểm tra clean code
- [ ] Implement Auditor: kiểm tra compliance với architectural law
- [ ] Implement Auditor: kiểm tra quality trước khi DONE
- [ ] Implement Auditor output: APPROVED / REVISE / ESCALATE
- [ ] Unit test cho Auditor Agent

## 3.7. Supreme Mentor Agent
- [ ] Implement Mentor: xử lý deadlock
- [ ] Implement Mentor: đưa ra quyết định chiến lược
- [ ] Implement Mentor: giải quyết mâu thuẫn giữa spec, code và review
- [ ] Implement Mentor: refactor workflow nếu cần
- [ ] Implement Mentor: đưa ra final verdict
- [ ] Unit test cho Mentor Agent

## 3.8. DevOps/Deployment Agent
- [ ] Implement DevOps: build image
- [ ] Implement DevOps: chạy Docker
- [ ] Implement DevOps: deploy staging
- [ ] Implement DevOps: quản lý CI/CD
- [ ] Implement DevOps: theo dõi logs
- [ ] Implement DevOps: rollback nếu cần
- [ ] Unit test cho DevOps Agent

## 3.9. Monitoring/Maintenance Agent
- [ ] Implement Monitoring: theo dõi lỗi
- [ ] Implement Monitoring: phát hiện anomaly
- [ ] Implement Monitoring: cảnh báo regressions
- [ ] Implement Monitoring: gom feedback thành bug report
- [ ] Implement Monitoring: hỗ trợ cải tiến hệ thống
- [ ] Unit test cho Monitoring Agent

## 3.10. Agent Integration Tests
- [ ] Test: Gatekeeper → Orchestrator → Specialist → Auditor → Done
- [ ] Test: Escalation flow (Specialist fail → Mentor takeover)
- [ ] Test: Model routing theo complexity
- [ ] Test: Context builder với task phức tạp

---

# PHASE 4 — VERIFICATION SANDBOX (2–3 tuần)

## 4.1. Docker Sandbox Manager
- [ ] Implement create container function
- [ ] Implement mount repo vào container
- [ ] Implement run tests trong container
- [ ] Implement capture logs từ container
- [ ] Implement destroy container sau khi hoàn thành
- [ ] Implement container timeout
- [ ] Implement resource limits (CPU, RAM) cho container
- [ ] Unit test cho Docker Sandbox Manager

## 4.2. Verification Pipeline
- [ ] Implement lint step
- [ ] Implement unit test step
- [ ] Implement integration test step
- [ ] Implement build step
- [ ] Implement security scan step
- [ ] Implement pipeline orchestration (chạy tuần tự hoặc song song)
- [ ] Implement pipeline result aggregation
- [ ] Unit test cho verification pipeline

## 4.3. Exit Code Validation
- [ ] Implement exit code parsing (exit code = 0 → VERIFIED)
- [ ] Implement error message extraction
- [ ] Implement test result parsing
- [ ] Implement verification status update
- [ ] Build API: POST /tasks/{task_id}/verify
- [ ] Build API: GET /tasks/{task_id}/verification-result
- [ ] Unit test cho exit code validation

## 4.4. Rollback Engine
- [ ] Implement revert branch function
- [ ] Implement restore snapshot function
- [ ] Implement rollback trigger (verification fail)
- [ ] Implement rollback audit logging
- [ ] Build API: POST /tasks/{task_id}/rollback
- [ ] Unit test cho rollback engine

## 4.5. Sandbox Integration
- [ ] Tích hợp sandbox vào workflow (node Verify)
- [ ] Implement sandbox result → state update
- [ ] Implement sandbox fail → retry/escalate
- [ ] Integration test: code → sandbox → verify → update state

## 4.6. CI/CD Integration
- [ ] Setup GitHub Actions / GitLab CI
- [ ] Implement CI trigger từ workflow
- [ ] Implement CI result callback
- [ ] Test CI/CD integration

---

# PHASE 5 — GOVERNANCE LAYER (2 tuần)

## 5.1. Confidence Engine
- [ ] Implement confidence scoring formula: Confidence = (T × 0.35) + (L × 0.15) - (P × 0.20) + (A × 0.30)
- [ ] Implement test pass rate calculation (T)
- [ ] Implement lint/code quality score (L)
- [ ] Implement retry penalty calculation (P)
- [ ] Implement architectural law compliance score (A)
- [ ] Implement confidence threshold rules (cao → auto, thấp → escalate, quá thấp → takeover/rollback)
- [ ] Build API: GET /tasks/{task_id}/confidence
- [ ] Unit test cho confidence engine

## 5.2. Architectural Law Engine
- [ ] Implement luật loader từ laws.yaml/laws.json
- [ ] Implement clean architecture checker
- [ ] Implement validation checker
- [ ] Implement forbidden patterns detector
- [ ] Implement law violation reporting
- [ ] Build API: GET /laws
- [ ] Build API: POST /laws
- [ ] Build API: GET /tasks/{task_id}/law-violations
- [ ] Unit test cho architectural law engine

## 5.3. Cost Governor
- [ ] Implement token usage tracking
- [ ] Implement mentor calls tracking
- [ ] Implement retry loop tracking
- [ ] Implement daily mentor call limit
- [ ] Implement cost alerting
- [ ] Implement cost governor rules (task nhỏ → Flash, trung bình → Pro, lớn → Mentor)
- [ ] Build API: GET /cost-stats
- [ ] Build API: GET /cost-stats/{project_id}
- [ ] Unit test cho cost governor

## 5.4. Risk Classification
- [ ] Implement risk classification: LOW / HIGH / CRITICAL
- [ ] Implement action mapping: LOW → auto approve, HIGH → require audit, CRITICAL → require human approval
- [ ] Implement risk scoring cho task
- [ ] Build API: GET /tasks/{task_id}/risk
- [ ] Unit test cho risk classification

## 5.5. Governance Integration
- [ ] Tích hợp confidence engine vào workflow
- [ ] Tích hợp architectural law engine vào Auditor node
- [ ] Tích hợp cost governor vào model router
- [ ] Tích hợp risk classification vào task assignment
- [ ] Integration test: governance layer end-to-end

---

# PHASE 6 — MEMORY SYSTEM (2–3 tuần)

## 6.1. Instruction Ledger
- [ ] Tạo model MentorInstruction (SQLAlchemy)
- [ ] Implement mentor advice storage
- [ ] Implement failed patterns storage
- [ ] Implement architecture decisions storage
- [ ] Implement lesson learned storage
- [ ] Build API: GET /instructions
- [ ] Build API: POST /instructions
- [ ] Build API: GET /instructions/{task_id}
- [ ] Unit test cho instruction ledger

## 6.2. Semantic Retrieval
- [ ] Setup pgvector trong PostgreSQL
- [ ] Implement embedding generation (OpenAI / BGE)
- [ ] Implement vector storage cho memory
- [ ] Implement semantic search: new task → search memory → reuse solution
- [ ] Implement similarity threshold
- [ ] Build API: POST /memory/search
- [ ] Unit test cho semantic retrieval

## 6.3. Decision History
- [ ] Tạo model DecisionHistory (SQLAlchemy)
- [ ] Implement decision storage (decision, reason, context)
- [ ] Implement decision retrieval
- [ ] Build API: GET /decisions
- [ ] Build API: POST /decisions
- [ ] Build API: GET /decisions/{project_id}
- [ ] Unit test cho decision history

## 6.4. Memory Integration
- [ ] Tích hợp memory vào Gatekeeper (tra cứu task cũ)
- [ ] Tích hợp memory vào Orchestrator (reuse solution)
- [ ] Tích hợp memory vào Specialist (learn from past)
- [ ] Implement memory update sau mỗi task hoàn thành
- [ ] Integration test: memory system end-to-end

## 6.5. Cache Layer
- [ ] Implement Redis cache cho frequent queries
- [ ] Implement cache invalidation strategy
- [ ] Implement cache TTL
- [ ] Unit test cho cache layer

---

# PHASE 7 — DASHBOARD & OBSERVABILITY (2–3 tuần)

## 7.1. Frontend Setup
- [ ] Setup Next.js project
- [ ] Setup TailwindCSS
- [ ] Setup Zustand (state management)
- [ ] Setup Recharts (charts)
- [ ] Cấu hình routing
- [ ] Tạo layout cơ bản

## 7.2. Dashboard Pages
- [ ] Tạo trang: Project Overview
- [ ] Tạo trang: Task List (hiển thị status, confidence, retry count)
- [ ] Tạo trang: Workflow Graph (trạng thái hệ thống)
- [ ] Tạo trang: Agent Status (agent đang làm gì)
- [ ] Tạo trang: Mentor Calls (cost tracking)
- [ ] Tạo trang: Failures & Bottlenecks
- [ ] Tạo trang: Audit Logs
- [ ] Tạo trang: Memory/Instructions

## 7.3. Dashboard Components
- [ ] Component: Task Card (hiển thị task info, status, confidence)
- [ ] Component: Workflow Visualization (state machine diagram)
- [ ] Component: Confidence Gauge
- [ ] Component: Retry Counter
- [ ] Component: Cost Chart
- [ ] Component: Agent Activity Feed
- [ ] Component: Alert Banner

## 7.4. Dashboard API Integration
- [ ] Connect dashboard đến backend API
- [ ] Implement real-time updates (WebSocket / SSE)
- [ ] Implement pagination cho task list
- [ ] Implement filtering và sorting
- [ ] Test dashboard integration

## 7.5. Monitoring Stack
- [ ] Setup Prometheus (metrics)
- [ ] Setup Loki (logs)
- [ ] Setup Grafana (visualization)
- [ ] Setup OpenTelemetry (tracing)
- [ ] Cấu hình Grafana dashboards
- [ ] Cấu hình alert rules
- [ ] Test monitoring stack

## 7.6. Observability Integration
- [ ] Implement OpenTelemetry instrumentation trong agents
- [ ] Implement metrics export (task duration, success rate, cost)
- [ ] Implement log aggregation
- [ ] Implement distributed tracing
- [ ] Test observability end-to-end

---

# PHASE 8 — DEPLOYMENT & OPERATIONS (2–3 tuần)

## 8.1. Staging Deployment
- [ ] Implement AI tự build image
- [ ] Implement AI tự deploy staging
- [ ] Implement AI tự verify staging
- [ ] Build API: POST /deploy/staging
- [ ] Build API: GET /deploy/staging/{deployment_id}
- [ ] Unit test cho staging deployment

## 8.2. Production Approval
- [ ] Implement human approval workflow cho critical tasks
- [ ] Implement approval UI trong dashboard
- [ ] Implement approval API
- [ ] Implement approval timeout handling
- [ ] Build API: POST /deploy/production/request
- [ ] Build API: POST /deploy/production/approve
- [ ] Build API: POST /deploy/production/reject
- [ ] Unit test cho production approval

## 8.3. Rollback Strategy
- [ ] Implement auto rollback khi deploy fail
- [ ] Implement notify user khi rollback
- [ ] Implement rollback audit logging
- [ ] Build API: POST /deploy/rollback
- [ ] Unit test cho rollback strategy

## 8.4. CI/CD Pipeline
- [ ] Setup GitHub Actions / GitLab CI pipeline
- [ ] Implement automated testing trong CI
- [ ] Implement automated build trong CI
- [ ] Implement automated staging deploy trong CI
- [ ] Implement CI/CD status callback
- [ ] Test CI/CD pipeline

## 8.5. Container Orchestration
- [ ] Setup Docker Compose cho development
- [ ] Setup Kubernetes / Docker Swarm cho production (optional)
- [ ] Implement health checks
- [ ] Implement auto-restart policies
- [ ] Implement resource limits
- [ ] Test container orchestration

## 8.6. Reverse Proxy & Cloud
- [ ] Setup Nginx reverse proxy
- [ ] Setup SSL/TLS
- [ ] Deploy lên cloud (AWS / Hetzner / GCP)
- [ ] Configure DNS
- [ ] Test production deployment

## 8.7. Operations Integration
- [ ] Tích hợp monitoring vào deployment pipeline
- [ ] Implement deployment audit logging
- [ ] Implement deployment metrics
- [ ] Integration test: deploy → monitor → rollback

---

# PHASE 9 — OPTIMIZATION & AUTONOMY (Liên tục)

## 9.1. Multi-Project Orchestration
- [ ] Implement AI quản lý nhiều project cùng lúc
- [ ] Implement resource allocation giữa các project
- [ ] Implement priority management
- [ ] Implement cross-project dependency handling
- [ ] Test multi-project orchestration

## 9.2. Self-Improving Workflows
- [ ] Implement Mentor tối ưu prompts
- [ ] Implement Mentor tối ưu routing
- [ ] Implement Mentor tối ưu governance
- [ ] Implement workflow performance analysis
- [ ] Implement automatic workflow adjustment
- [ ] Test self-improving workflows

## 9.3. Autonomous Refactoring
- [ ] Implement AI detect tech debt
- [ ] Implement AI suggest cleanup
- [ ] Implement AI optimize architecture
- [ ] Implement refactoring approval workflow
- [ ] Test autonomous refactoring

## 9.4. Performance Optimization
- [ ] Optimize model call latency
- [ ] Optimize database queries
- [ ] Optimize cache hit rate
- [ ] Optimize container startup time
- [ ] Benchmark và đo lường performance

## 9.5. Scalability
- [ ] Implement horizontal scaling cho agents
- [ ] Implement load balancing
- [ ] Implement queue-based task distribution
- [ ] Stress test hệ thống
- [ ] Optimize cho scale

## 9.6. Continuous Improvement
- [ ] Thu thập metrics và feedback
- [ ] Phân tích bottleneck
- [ ] Cải thiện prompts
- [ ] Cải thiện workflow
- [ ] Cải thiện governance rules
- [ ] Lặp lại quá trình optimization

---

# MVP — END-TO-END WORKFLOW (Ưu tiên cao nhất)

## Mục tiêu: AI hoàn thành 1 task kỹ thuật theo workflow có governance
## Ví dụ: "Tạo auth module"

### MVP Tasks
- [ ] Setup repo monorepo
- [ ] Build PostgreSQL schema (tasks, projects, modules, audit_logs)
- [ ] Build workflow state machine: NEW → DONE
- [ ] Build ONE end-to-end workflow:
  - [ ] User input: "Tạo auth module"
  - [ ] Gatekeeper: phân loại task
  - [ ] Orchestrator: chia task nhỏ
  - [ ] Specialist: code auth module
  - [ ] Sandbox: test auth module
  - [ ] Auditor: review code
  - [ ] Update state → DONE
- [ ] Test MVP end-to-end

---

# TỔNG KẾT THỨ TỰ ƯU TIÊN

1. **State** → Phase 0 + Phase 1
2. **Workflow** → Phase 2
3. **Verification** → Phase 4
4. **Governance** → Phase 5
5. **Memory** → Phase 6
6. **Dashboard** → Phase 7
7. **Deployment** → Phase 8
8. **Optimization** → Phase 9

---

# CÔNG NGHỆ SỬ DỤNG

| Thành phần | Tech |
|---|---|
| Core orchestration | LangGraph, Python |
| Backend API | FastAPI |
| Database | PostgreSQL, pgvector |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Cache/Queue | Redis |
| Sandbox | Docker, Ubuntu |
| CI/CD | GitHub Actions |
| Frontend | Next.js, TailwindCSS, Recharts, Zustand |
| Monitoring | Prometheus, Loki, Grafana, OpenTelemetry |
| Reverse Proxy | Nginx |
| Cloud | AWS / Hetzner / GCP |
| Vector Search | pgvector |
| Embeddings | OpenAI / BGE |
