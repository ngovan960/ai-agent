# MVP Scope Definition — AI SDLC System

> Tài liệu này định nghĩa phạm vi MVP (Minimum Viable Product) cho hệ thống AI SDLC. Dự án ban đầu quá tham vọng (358 tasks, 10 phases). MVP này cắt giảm xuống mức的现实 khả thi để chứng minh core workflow hoạt động end-to-end.

---

## 1. MVP Philosophy

Nguyên tắc thiết kế MVP: **chứng minh core workflow hoạt động từ đầu đến cuối** trước khi mở rộng.

### 4 Nguyên tắc cốt lõi

1. **Prove the core workflow works end-to-end** — Một task đi qua toàn bộ pipeline từ NEW → DONE, không cần tất cả features phải hoàn hảo.

2. **One task type: "Create a module/feature"** — MVP chỉ hỗ trợ đúng một loại task. Không refactor, không debug, không migration. Chỉ tạo module/feature mới. Điều này giảm complexity của workflow engine và agent system đáng kể.

3. **Minimal viable agents, minimal viable governance** — Agents trong MVP chỉ cần đủ khả năng để hoàn thành workflow. Governance chỉ cần đủ để audit state transitions và retry. Không cần memory system, không cần decision history.

4. **Focus on state machine + workflow + 1 agent cycle** — Ba thành phần cốt lõi: **state machine** (định nghĩa các trạng thái hợp lệ), **workflow engine** (chạy state machine), và **1 agent cycle** (Orchestrator → Specialist → Auditor). Nếu ba thành phần này hoạt động, mọi thứ khác có thể xây dựng trên nền tảng đó.

### Tư tưởng dẫn hướng

- **Done is better than perfect** — Ship MVP nhanh, iterate sau.
- **Vertical slice over horizontal layering** — Thà một pipeline hoạt động end-to-end còn hơn 10 features dở dang.
- **Explicit exclusion is as important as inclusion** — Danh sách "OUT" (phần 3) phải được tôn trọng nghiêm ngặt.

---

## 2. MVP Scope — What's IN

### Phase 1 — Core State System (2-3 weeks)

Mục tiêu: Xây dựng nền tảng dữ liệu và state machine infrastructure.

| Component | Chi tiết | Ưu tiên |
|-----------|----------|---------|
| PostgreSQL database setup | Schema cho projects, modules, tasks, state_transitions, audit_logs, retry_records | P0 |
| Project/Module/Task CRUD APIs | REST API cho tạo, đọc, cập nhật, xóa projects, modules, tasks | P0 |
| State transition engine | Engine validate và thực hiện 18 state transitions theo state machine definition; mỗi transition được validate trước khi thực hiện | P0 |
| Audit logging (middleware) | Middleware tự động ghi log mọi state transition:谁 (who), khi nào (when), từ đâu (from_state), đến đâu (to_state), lý do (reason) | P0 |
| Basic retry tracking | Theo dõi số lần retry per task; max 2 retries; sau khi vượt max → tự động chuyển sang ESCALATED | P1 |

**Deliverables:**
- Database schema migrations
- CRUD API endpoints sử dụng Express/Fastify
- State transition engine có unit test cho tất cả 18 transitions
- Audit log middleware tích hợp vào API
- Retry tracking table và logic

**Database Schema tóm tắt:**
```
projects: id, name, description, created_at, updated_at
modules:  id, project_id, name, description, tech_stack, created_at
tasks:    id, module_id, title, description, state, retry_count, max_retries, created_at, updated_at
state_transitions: id, task_id, from_state, to_state, reason, metadata, created_at
audit_logs:        id, entity_type, entity_id, action, actor, details, created_at
retry_records:     id, task_id, attempt, result, created_at
```

### Phase 2 — Workflow Engine (2-3 weeks)

Mục tiêu: Engine chạy state machine tự động, điều phối agents và quản lý dependencies.

| Component | Chi tiết | Ưu tiên |
|-----------|----------|---------|
| Workflow engine core | State machine runner nhận task ở state hiện tại, quyết định transition tiếp theo, invoke agent tương ứng, chờ kết quả, thực hiện transition | P0 |
| 7 workflow nodes | Mỗi node tương ứng với một state: NEW (nhận task), ANALYZING (phân tích), PLANNING (lập kế hoạch), IMPLEMENTING (thực hiện), VERIFYING (kiểm chứng), REVIEWING (review), DONE/ESCALATED (kết thúc) | P0 |
| Dependency management (basic) | Tasks có thể depend trên tasks khác; workflow engine không bắt task cho đến khi dependencies hoàn thành (state = DONE) | P1 |
| Gatekeeper agent (basic classification) | Phân loại task complexity: TRIVIAL / STANDARD / COMPLEX. Dựa vào keyword matching + heuristic rules. Không cần LLM cho MVP—có thể dùng LLM nếu sẵn có nhưng fallback về heuristic | P1 |
| Orchestrator agent (basic task breakdown) | Nhận task "Create X module" → break down thành sub-tasks: tạo file structure, implement logic, write tests. MVP: dùng LLM với prompt template cố định | P0 |

**Workflow Node Definitions:**

```
NEW → ANALYZING
  - Gatekeeper phân loại complexity
  - Gán model phù hợp (qua model router)

ANALYZING → PLANNING
  - Orchestrator break down task thành sub-tasks
  - Tạo dependency graph

PLANNING → IMPLEMENTING
  - Specialist agent thực hiện code generation
  - Mỗi sub-task được xử lý tuần tự

IMPLEMENTING → VERIFYING
  - Chạy lint + test verification pipeline
  - Nếu fail → retry hoặc ESCALATED

VERIFYING → REVIEWING
  - Auditor agent review code
  - Kiểm tra code quality standards

REVIEWING → DONE (pass) | REVIEWING → ESCALATED (fail sau max retries)

ESCALATED → (chờ human intervention, không tự động xử lý trong MVP)
```

### Phase 3 — Agent Runtime (2-3 weeks)

Mục tiêu: Hệ thống agents thực hiện công việc thực tế—code generation, review, và routing.

| Component | Chi tiết | Ưu tiên |
|-----------|----------|---------|
| OpenCode as execution brain | Sử dụng OpenCode (đang chạy) làm execution layer cho tất cả agent calls. Agents không tự implement tool usage—chúng gọi OpenCode với instructions, OpenCode thực hiện qua bash/edit/write/read tools | P0 |
| Specialist agent (code generation) | Nhận task specification → generate code. Sử dụng OpenCode Dev mode: write files, edit existing code. Output: source code files cho module | P0 |
| Auditor agent (basic code review) | Nhận generate code → review. Kiểm tra: naming conventions, error handling, security basics, test coverage. Output: APPROVE / REJECT + lý do | P0 |
| Model router (complexity-based) | Route LLM calls dựa trên task complexity: TRIVIAL → fast/cheap model, STANDARD → balanced model, COMPLEX → capable model. MVP: mapping cố định, không dynamic routing | P1 |
| Prompt template system | Repository các prompt templates cho mỗi agent type. Templates hỗ trợ variable interpolation. Lưu trong database, có thể update mà không cần deploy lại | P1 |
| Context builder (basic) | Build context cho LLM call: task description + module spec + relevant existing code + conventions. MVP: simple concatenation với truncation strategy khi vượt token limit | P1 |

**Agent Architecture:**

```
┌─────────────────────────────────────────────┐
│              Workflow Engine                 │
│  (chạy state machine, invoke agents)        │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │  Agent Runtime  │
       │                 │
       │  ┌───────────┐  │
       │  │Gatekeeper  │  │──→ classify complexity
       │  └───────────┘  │
       │  ┌───────────┐  │
       │  │Orchestrator│  │──→ break down task
       │  └───────────┘  │
       │  ┌───────────┐  │
       │  │Specialist  │──┼──→ OpenCode Dev mode
       │  └───────────┘  │     (bash, edit, write, read)
       │  ┌───────────┐  │
       │  │Auditor    │──┼──→ OpenCode Review mode
       │  └───────────┘  │
       │  ┌───────────┐  │
       │  │Model Router│  │──→ select model by complexity
       │  └───────────┘  │
       └─────────────────┘
```

**Prompt Template Example (Specialist):**

```yaml
name: specialist-implement
description: "Code generation prompt cho Specialist agent"
template: |
  You are a specialist developer implementing a module.

  ## Task
  {{task_description}}

  ## Module Specification
  {{module_spec}}

  ## Existing Code Context
  {{existing_code}}

  ## Conventions
  {{conventions}}

  ## Requirements
  - Follow the module specification precisely
  - Use the existing code style and patterns
  - Include error handling
  - Write code that is testable
  - Do NOT add comments unless critical for understanding

  Implement the module as specified.
variables:
  - task_description
  - module_spec
  - existing_code
  - conventions
```

### Phase 4 — Verification (1-2 weeks)

Mục tiêu: Kiểm chứng output của Specialist agent và rollback khi cần.

| Component | Chi tiết | Ưu tiên |
|-----------|----------|---------|
| OpenCode dev mode verification | Sử dụng OpenCode's bash tool để chạy lệnh verification: lint, test, build. Không cần custom verification system—reuse existing OpenCode capabilities | P0 |
| Lint + test verification pipeline | Define verification steps per project: eslint, prettier, jest/vitest. Workflow engine gọi OpenCode chạy các lệnh này sau IMPLEMENTING state | P0 |
| Basic rollback on failure | Nếu verification fail, rollback file changes (dùng git). Nếu retry count < max, retry IMPLEMENTING. Nếu retry count >= max, chuyển sang ESCALATED | P1 |

**Verification Pipeline Flow:**

```
IMPLEMENTING hoàn thành
       │
       ▼
  ┌─────────────┐
  │ Git commit   │  ← checkpoint trước khi verify
  │ working dir  │
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Run linter  │  ← OpenCode: bash "npm run lint"
  └──────┬──────┘
         │ pass?
    ┌────┴────┐
   yes        no
    │          │
    ▼          ▼
  ┌─────┐  ┌──────────────┐
  │Test │  │ Rollback git  │
  │Run  │  │ retry_count++ │
  └──┬──┘  │ retry: back to│
     │     │ IMPLEMENTING  │
  pass?    │ max: ESCALATED│
  ┌──┴──┐  └──────────────┘
 yes    no
  │      │
  ▼      └──→ (same retry logic)
REVIEWING
```

### TOTAL MVP Timeline

| Phase | Duration | Cumulative |
|-------|----------|-----------|
| Phase 1 — Core State System | 2-3 weeks | 2-3 weeks |
| Phase 2 — Workflow Engine | 2-3 weeks | 4-6 weeks |
| Phase 3 — Agent Runtime | 2-3 weeks | 6-9 weeks |
| Phase 4 — Verification | 1-2 weeks | 7-11 weeks |

**Total MVP: ~8-11 weeks**

Note: Các phases có thể overlap. Phase 2 có thể bắt đầu khi Phase 1 gần xong (database schema stable). Phase 3 có thể bắt đầu khi Phase 2's workflow engine core hoàn thành.

---

## 3. MVP Scope — What's OUT

Những features sau đây **không** thuộc MVP. Chúng sẽ được xây dựng trong các phases sau khi MVP chứng minh được core workflow hoạt động.

### Governance & Memory (Post-MVP Phase 5-6)

| Feature | Lý do loại khỏi MVP | Khi nào xây dựng |
|---------|---------------------|-----------------|
| **Mentor takeover mode** | Complexity cao, cần agent handoff protocol phức tạp. MVP chỉ cần ESCALATE về human | Phase 5 |
| **Memory system (pgvector)** | Cần pgvector extension, embedding pipeline, similarity search. Overkill cho MVP—LIKE query đủ dùng | Phase 6 |
| **Instruction ledger** | Immutable instruction store cần event sourcing pattern. MVP dùng prompt templates trong DB | Phase 6 |
| **Decision history** | Cần separate service cho decision tracking. MVP chỉ cần audit_logs cho state transitions | Phase 5 |
| **Risk classification engine** | Rule-based risk assessment cần extensive rules. MVP dùng Gatekeeper heuristic classification | Phase 5 |

### Frontend & Observability (Post-MVP Phase 7-8)

| Feature | Lý do loại khỏi MVP | Khi nào xây dựng |
|---------|---------------------|-----------------|
| **Dashboard (Next.js frontend)** | Frontend cần designer, separate build pipeline. MVP dùng API + CLI interface | Phase 7 |
| **Monitoring stack (Prometheus/Grafana)** | Cần infrastructure setup, alerting rules. MVP chỉ cần application-level logging | Phase 7 |
| **Production deployment (Docker sandbox)** | Docker sandbox cần security hardening, resource limits. MVP chạy trực tiếp trên host | Phase 8 |

### Advanced Features (Post-MVP Phase 9+)

| Feature | Lý do loại khỏi MVP | Khi nào xây dựng |
|---------|---------------------|-----------------|
| **CI/CD integration** | Cần adapter cho từng CI/CD platform. MVP verification chạy local qua OpenCode | Phase 8 |
| **Multi-project orchestration** | Cần project isolation, resource sharing. MVP chỉ hỗ trợ single project | Phase 9+ |
| **Self-improving workflows** | Cần feedback loop, metrics collection, A/B testing. MVP chỉ collect data, không tự improve | Phase 9+ |
| **Autonomous refactoring** | Task type "refactor" cần deeper code understanding. MVP chỉ support "create module/feature" | Phase 9+ |
| **Production approval workflow** | Cần multi-role approval, RBAC. MVP chỉ có single user mode | Phase 8 |
| **Cost governor** | Cần token tracking, budget thresholds, throttling. MVP chỉ track cost, không throttle | Phase 9+ |

### Tóm tắt: Đừng xây dựng những thứ này trong MVP

```
❌ Mentor takeover mode
❌ Memory system (pgvector + embedding pipeline)
❌ Instruction ledger (event sourcing)
❌ Decision history (separate service)
❌ Dashboard (Next.js frontend)
❌ Monitoring stack (Prometheus/Grafana)
❌ Production deployment (Docker sandbox)
❌ CI/CD integration
❌ Multi-project orchestration
❌ Self-improving workflows
❌ Autonomous refactoring (task type)
❌ Production approval workflow
❌ Cost governor
❌ Risk classification engine
```

---

## 4. MVP Success Criteria

MVP được coi là thành công khi tất cả các criteria sau đạt được:

### 4.1 End-to-End Workflow

- [ ] User có thể input task "Create auth module" qua API
- [ ] Task đi qua đầy đủ pipeline: **NEW → ANALYZING → PLANNING → IMPLEMENTING → VERIFYING → REVIEWING → DONE**
- [ ] Mỗi state transition được validate và audited
- [ ] Task kết thúc ở state DONE (thành công) hoặc ESCALATED (fail sau max retries)

### 4.2 Agent Performance

- [ ] **Specialist agent** generate code trong Dev mode via OpenCode (sử dụng bash, edit, write tools)
- [ ] **Auditor agent** review generated code và trả về APPROVE hoặc REJECT với lý do cụ thể
- [ ] **Gatekeeper agent** classify task complexity (TRIVIAL / STANDARD / COMPLEX)
- [ ] **Orchestrator agent** break down task thành sub-tasks với dependency ordering

### 4.3 State Machine Integrity

- [ ] Tất cả 18 state transitions được validate đúng theo state machine definition
- [ ] Invalid transitions bị reject (ví dụ: không thể chuyển từ DONE → IMPLEMENTING)
- [ ] Audit log ghi lại mọi transition: who, when, from_state, to_state, reason
- [ ] State history có thể được traced cho bất kỳ task nào

### 4.4 Retry & Escalation

- [ ] Retry tracking hoạt động: đếm số lần retry per task
- [ ] Max 2 retries — sau đó tự động chuyển sang ESCALATED
- [ ] ESCALATED tasks rõ ràng bị flag và không tự động retry thêm
- [ ] Human có thể manually retry ESCALATED tasks qua API

### 4.5 Architectural Laws

- [ ] Tất cả 20 architectural laws đều **enforceable** (có thể kiểm tra) thông qua Auditor agent prompts và verification pipeline
- [ ] Kiểm tra thủ công: tạo một task và verify rằng output tuân thủ ít nhất 5 laws chính

### 4.6 Measurable Targets

| Metric | MVP Target | Measurement Method |
|--------|-----------|-------------------|
| End-to-end completion rate | > 50% tasks reach DONE | Query tasks where state = DONE vs total |
| State transition accuracy | 100% valid transitions | Count invalid transition attempts |
| Audit log completeness | 100% transitions logged | Compare audit_logs count vs state_transitions count |
| Retry tracking accuracy | 100% retries tracked | Verify retry_records matches actual retries |
| Agent call success rate | > 70% LLM calls succeed | Log LLM call outcomes |
| Average task completion time | < 30 minutes per task | Timestamps: created_at → DONE_at |

---

## 5. MVP Technical Decisions

### 5.1 Execution Layer: OpenCode as Brain

**Decision:** Sử dụng OpenCode (đang chạy) làm execution brain cho tất cả agent calls.

**Context:** MVP cần một cách để agents tương tác với filesystem và chạy commands. Xây dụng custom tool system sẽ mất 2-3 tuần额外. OpenCode đã có bash, edit, write, read tools.

**Consequences:**
- ✅ Giảm đáng kể development time—không cần xây dựng custom tool system
- ✅ OpenCode tools đã được battle-tested
- ⚠️ Agents phụ thuộc vào OpenCode runtime—nếu OpenCode down, agents không hoạt động
- ⚠️ Cần careful prompt engineering để agents sử dụng đúng tools

**Implementation:**
```
Agent → Workflow Engine → OpenCode API → tool calls (bash/edit/write/read)
```

### 5.2 Verification: OpenCode Dev Mode

**Decision:** Sử dụng existing OpenCode tools (bash) cho Dev mode verification.

**Context:** Verification trong MVP chỉ cần chạy lint + test. OpenCode's bash tool có thể execute `npm run lint` và `npm run test`.

**Consequences:**
- ✅ Không cần xây dựng separate verification infrastructure
- ✅ Reuse existing capabilities
- ⚠️ Verification chạy trên same machine—không sandbox isolation
- ⚠️ Cần git-based rollback strategy vì không có container isolation

**Implementation:**
```bash
# Verification steps via OpenCode bash tool
npm run lint          # Step 1: Lint check
npm run test          # Step 2: Test run
npm run build         # Step 3: Build check (optional per project)
```

### 5.3 Sandboxing: Skip Docker cho MVP

**Decision:** Bỏ qua Docker sandbox cho MVP. Chạy mọi thứ trực tiếp trên host.

**Context:** Docker sandbox cần image building, resource limits, security policies, volume mounts. Ước tính 2-3 weeks额外. MVP verification chạy local qua OpenCode bash tool.

**Consequences:**
- ✅ Tiết kiệm 2-3 weeks development time
- ⚠️ Không có sandbox isolation—agents có potential ảnh hưởng host system
- ⚠️ Cần manual cleanup nếu agent generate ra unwanted files
- 🔜 Docker sandbox sẽ được thêm trong Phase 8

**Mitigation:**
- Agents chạy trong git-tracked directory—có thể rollback
- OpenCode bash commands được log đầy đủ trong audit_logs
- Human review trước khi ESCALATED tasks được retry

### 5.4 Frontend: Skip Next.js Dashboard cho MVP

**Decision:** MVP sử dụng API + CLI interface. Không xây dựng Next.js dashboard.

**Context:** Dashboard cần designer, frontend build pipeline, component library, API integration. Ước tính 2-3 weeks. MVP chỉ cần cách để submit tasks và check status.

**Consequences:**
- ✅ Tiết kiệm 2-3 weeks development time
- ✅ Team focus hoàn toàn vào backend + agent logic
- ⚠️ User experience kém hơn—phải dùng curl/CLI thay vì visual dashboard
- 🔜 Next.js dashboard sẽ được thêm trong Phase 7

**MVP Interface:**
```bash
# Submit task
curl -X POST /api/tasks -d '{"title": "Create auth module", "module_id": "..."}'

# Check task status
curl /api/tasks/{task_id}

# List tasks
curl /api/tasks?project_id=...

# Retry escalated task
curl -X POST /api/tasks/{task_id}/retry
```

### 5.5 Memory: Skip pgvector cho MVP

**Decision:** MVP sử dụng PostgreSQL LIKE queries cho basic memory search. Không cài pgvector.

**Context:** pgvector cần extension installation, embedding pipeline, similarity search indexing. MVP chỉ cần basic text search—"find previous tasks similar to X".

**Consequences:**
- ✅ Giảm infrastructure complexity
- ✅ Không cần embedding model hoặc vector transformation pipeline
- ⚠️ Search quality thấp hơn—full-text search thay vì semantic search
- ⚠️ Không thể search bằng meaning/intent, chỉ search bằng keyword
- 🔜 pgvector sẽ được thêm trong Phase 6

**MVP Memory Query Example:**
```sql
-- Tìm tasks tương tự (basic keyword matching)
SELECT * FROM tasks
WHERE description ILIKE '%auth%'
   OR description ILIKE '%authentication%'
   OR title ILIKE '%auth%'
ORDER BY created_at DESC
LIMIT 10;
```

### 5.6 Caching: Skip Redis cho MVP

**Decision:** MVP sử dụng PostgreSQL cho tất cả data storage. Không cài Redis.

**Context:** Redis cần separate service, connection management, cache invalidation logic. MVP không có performance requirements cần in-memory caching.

**Consequences:**
- ✅ Simpler infrastructure—chỉ cần PostgreSQL
- ✅ Giảm operational complexity
- ⚠️ LLM response caching không available—mỗi call là fresh call
- ⚠️ State transition reads hit database mỗi lần
- 🔜 Redis sẽ được cân nhắc lại nếu performance là vấn đề post-MVP

**Data Flow (MVP):**
```
All reads/writes → PostgreSQL
No cache layer
No queue system (synchronous processing)
```

### Decision Summary Table

| Decision | MVP Choice | Post-MVP Target | Switching Cost |
|----------|-----------|-----------------|---------------|
| Execution layer | OpenCode | Custom tool system | Medium |
| Verification | OpenCode bash | Docker sandbox | Medium |
| Sandboxing | None (host) | Docker containers | High |
| Frontend | API + CLI | Next.js dashboard | Medium |
| Memory search | PostgreSQL LIKE | pgvector semantic | Medium |
| Caching | PostgreSQL only | Redis cache layer | Low |
| Task types | "Create module" only | Multiple types | Low |

---

## 6. MVP Risk Assessment

### 6.1 LLM Quality Inconsistency

**Risk:** LLM output quality không đồng nhất—đôi khi tốt, đôi khi kém. Specialist có thể generate code không hoạt động, Auditor có thể miss obvious issues.

**Likelihood:** 🔴 High — Đây là nature của LLMs.

**Impact:** 🟡 Medium — Code không hoạt động sẽ bị verification pipeline bắt, nhưng Auditor miss issues khó phát hiện hơn.

**Mitigation:**
- Iterative prompt engineering—refine prompts dựa trên failure patterns
- Structured output schemas cho mỗi agent (JSON format)
- Temperature settings optimized cho deterministic output
- Multiple verification layers (lint → test → auditor review)
- Fallback: ESCALATED state cho tasks cần human judgment

**Contingency:** Nếu LLM quality quá thấp cho code generation, có thể:
1. Reduce task scope (smaller modules, simpler implementations)
2. Add human-in-the-loop checkpoint sau IMPLEMENTING state
3. Use template-based generation cho common patterns trước khi dùng LLM

### 6.2 State Machine Edge Cases

**Risk:** 18 state transitions có nhiều edge cases—race conditions, invalid transition sequences, stuck states.

**Likelihood:** 🟡 Medium — State machine logic phức tạp nhưng predictable.

**Impact:** 🔴 High — Stuck tasks không thể progress, breaking entire workflow.

**Mitigation:**
- Thorough unit testing cho tất cả 18 transitions
- Integration tests cho common paths (happy path + failure paths)
- Database constraints enforcing valid transitions
- Timeout mechanism cho tasks stuck quá lâu trong một state
- Manual "force transition" API cho stuck tasks
- Comprehensive audit logging để debug transition issues

**Contingency:** Nếu phát hiện thêm edge cases:
1. Add transition validation rules vào database
2. Implement state recovery script
3. Add admin API để manually move tasks giữa states

### 6.3 Context Window Limits

**Risk:** LLM context window có thể bị vượt khi build context cho complex modules—task description + module spec + existing code + conventions.

**Likelihood:** 🟡 Medium — Phụ thuộc vào module size.

**Impact:** 🟡 Medium — Truncated context → diminished code quality.

**Mitigation:**
- Context builder với truncation strategy: priority order — task description > module spec > conventions > existing code
- Smart context selection: chỉ include relevant portions của existing code
- Token counting trước khi gửi LLM call
- Adjust complexity classification: nếu context quá lớn, classify as COMPLEX để dùng model có context window lớn hơn
- Document token budgets per model

**Token Budget (MVP):**
```
Model A (fast):   8K context → task(1K) + spec(2K) + code(4K) + buffer(1K)
Model B (balanced): 32K context → task(1K) + spec(4K) + code(24K) + buffer(3K)
Model C (capable): 128K context → task(2K) + spec(8K) + code(110K) + buffer(8K)
```

### 6.4 Cost Overrun

**Risk:** LLM API calls tốn tiền. Không có cost governor trong MVP—có thể vượt budget nhanh chóng.

**Likelihood:** 🟡 Medium — Phụ thuộc vào usage volume.

**Impact:** 🟡 Medium — Over budget nhưng không system failure.

**Mitigation:**
- **Cost tracking from day 1** — Log mọi LLM call với token count và cost estimate
- Model router ưu tiên cheap models cho simple tasks
- Set per-task token budget limits
- Monitor cumulative cost daily
- Implement hard stop khi cumulative cost vượt threshold

**Cost Tracking (MVP):**
```sql
CREATE TABLE llm_call_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    agent_type VARCHAR(50),      -- 'gatekeeper', 'orchestrator', 'specialist', 'auditor'
    model VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6.5 OpenCode Dependency

**Risk:** MVP phụ thuộc hoàn toàn vào OpenCode cho execution. Nếu OpenCode có issue (crash, compatibility, rate limits), agents không thể hoạt động.

**Likelihood:** 🟢 Low — OpenCode đã stable và đang chạy.

**Impact:** 🔴 High — Entire agent system down nếu OpenCode down.

**Mitigation:**
- OpenCode health check trước mỗi agent call
- Graceful degradation: nếu OpenCode unreachable, chuyển task sang ESCALATED
- Retry logic cho OpenCode connection issues
- Document OpenCode alternative paths cho post-MVP

### Risk Matrix Summary

| Risk | Likelihood | Impact | Priority |
|------|-----------|--------|----------|
| LLM quality inconsistency | 🔴 High | 🟡 Medium | 1 |
| State machine edge cases | 🟡 Medium | 🔴 High | 2 |
| Context window limits | 🟡 Medium | 🟡 Medium | 3 |
| Cost overrun | 🟡 Medium | 🟡 Medium | 4 |
| OpenCode dependency | 🟢 Low | 🔴 High | 5 |

---

## 7. Post-MVP Priorities

Sau khi MVP chứng minh core workflow hoạt động, các phases sau sẽ được xây dựng theo thứ tự ưu tiên:

### Phase 5 — Governance (2 weeks)

Mục tiêu: Thêm governance layer cho production-readiness.

- **Decision history service** — Track mọi decision points trong workflow: Orchestrator decisions, Gatekeeper classifications, Auditor verdicts. Cho phép trace lại lý do cho mỗi outcome.
- **Mentor takeover mode** — Khi task ESCALATED, human mentor có thể "take over" workflow: review context, make decisions, hand back control. Agent handoff protocol.
- **Risk classification engine** — Rule-based risk assessment cho tasks: assess impact, likelihood, dependencies. Phân loại: LOW/MEDIUM/HIGH risk.
- **Enhanced audit logging** — Expand audit logs để capture hơn state transitions: LLM call logs, tool usage logs, cost events.

**Priority reasoning:** Governance là foundation cho confidence. Trước khi thêm features phức tạp hơn, cần确保 mọi decision được documented và traceable.

### Phase 6 — Memory (2-3 weeks)

Mục tiêu: Agents học được từ experience.

- **pgvector integration** — Install pgvector extension, build embedding pipeline, implement semantic search. Agents có thể search "similar past tasks" bằng meaning chứ không chỉ keyword.
- **Instruction ledger** — Immutable instruction store dùng event sourcing pattern. Mọi instruction cho agents được stored và versioned. Cho phép A/B test prompts.
- **Context memory** — Agents remember context từ previous tasks trong same project. Build累积 knowledge về project conventions, patterns, gotchas.
- **Learning feedback loop** — Collect outcomes (success/failure) cho mỗi approach, feed back vào future task planning.

**Priority reasoning:** Memory là single biggest improvement cho agent quality. Với memory, agents tránh lặp lại mistakes và leverage past successes.

### Phase 7 — Dashboard (2-3 weeks)

Mục tiêu: Visual interface cho monitoring và interaction.

- **Next.js dashboard** — Real-time task monitoring, state visualization, agent call logs. Project overview, task timeline, cost dashboard.
- **Task submission UI** — Form-based task submission thay vì curl. Template selection, module picker, complexity preview.
- **Monitoring stack** — Prometheus metrics (task duration, LLM call counts, costs, success rates) + Grafana dashboards. Alert rules cho anomalies.
- **WebSocket updates** — Real-time task state updates push đến dashboard. Không cần manual refresh.

**Priority reasoning:** Dashboard cho phép non-technical stakeholders observe và interact với system. Cần sau khi backend stable.

### Phase 8 — Deployment (2-3 weeks)

Mục tiêu: Production-ready deployment infrastructure.

- **Docker sandbox** — Agents chạy trong Docker containers: isolated filesystem, resource limits, network restrictions. Security hardening.
- **Production approval workflow** — Multi-role approval cho deployments: dev → staging → production. RBAC system.
- **CI/CD integration** — Connect với GitHub Actions, GitLab CI. Automatic deployment pipelines triggered bởi task completion.
- **Infrastructure as Code** — Terraform/Pulumi cho provisioning. Reproducible environments.

**Priority reasoning:** Deployment security và isolation là prerequisite cho production use, nhưng không cần cho MVP proof-of-concept.

### Phase 9 — Optimization (ongoing)

Mục tiêu: Continuous improvement.

- **Cost governor** — Real-time cost tracking, per-project budget, automatic throttling khi approaching limits. Cost prediction cho tasks trước khi execute.
- **Multi-project orchestration** — Cross-project task dependencies, shared resource pools, project-level isolation.
- **Self-improving workflows** — A/B test prompt templates, measure outcomes, automatically promote better versions. Meta-learning từ past executions.
- **Advanced task types** — Support refactor, debug, migration, documentation task types. Mỗi type có workflow customization.
- **Autonomous refactoring** — Agent identifies code that needs refactoring and creates tasks automatically.

**Priority reasoning:** Optimization là indefinite phase. Bắt đầu sau khi system stable và features complete.

### Post-MVP Roadmap

```
MVP Complete (Week 8-11)
     │
     ▼
Phase 5: Governance (2 weeks) ─── Week 10-13
     │
     ▼
Phase 6: Memory (2-3 weeks) ────── Week 12-16
     │
     ▼
Phase 7: Dashboard (2-3 weeks) ─── Week 15-19
     │
     ▼
Phase 8: Deployment (2-3 weeks) ── Week 18-22
     │
     ▼
Phase 9: Optimization (ongoing) ── Week 20+
```

---

> **Tóm lại:** MVP là vertical slice nhỏ nhất chứng minh được rằng state machine → workflow engine → agent runtime pipeline hoạt động end-to-end. Mọi thứ khác—governance, memory, dashboard, deployment, optimization—được xây incremental sau khi MVP thành công.