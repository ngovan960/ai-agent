# Risk Assessment - AI SDLC System

## Tài liệu Đánh giá Rủi ro

---

## 1. Tổng quan

Tài liệu này đánh giá rủi ro cho AI SDLC System theo 4 nhóm: **Technical**, **Operational**, **Financial**, và **Security**. Mỗi rủi ro được phân tích theo xác suất (probability) và tác động (impact), kèm theo biện pháp giảm thiểu (mitigation) và kế hoạch dự phòng (contingency).

### 1.1 Risk Matrix

```
Impact →   Low (1)        Medium (2)        High (3)         Critical (4)
Probability ↓
High (4)    MONITOR        MITIGATE          PRIORITIZE       ESCALATE
Medium (3)  ACCEPT          MITIGATE          PRIORITIZE       ESCALATE
Low (2)     ACCEPT          MONITOR           MITIGATE         PRIORITIZE
Very Low (1) IGNORE          ACCEPT            MONITOR           MITIGATE
```

**Risk Score** = Probability × Impact

| Score | Level | Action |
|-------|-------|--------|
| 1-3 | Low | Accept hoặc monitor |
| 4-6 | Medium | Mitigate |
| 8-9 | High | Prioritize |
| 12-16 | Critical | Escalate và immediate action |

---

## 2. Top 10 Risks với Mitigations

### Risk #1: LLM Quality Inconsistency

| Attribute | Detail |
|-----------|--------|
| **Category** | Technical |
| **Probability** | High (4) |
| **Impact** | High (3) |
| **Risk Score** | 12 — **CRITICAL** |
| **Description** | LLM output quality không đồng nhất. Cùng một prompt có thể tạo ra kết quả rất khác nhau điều phối code không hoạt động, Auditor miss obvious bugs, hoặc Orchestrator tạo kế hoạch kém. Bản chất của LLM: non-deterministic, hallucination, context sensitivity. |

**Impact Analysis:**

- Specialist tạo code không compile được → verification fail → retry → cost tăng
- Auditor miss critical bugs → code lỗi vào production
- Orchestrator tạo kế hoạch kém → sub-tasks không rõ ràng → cascade failure
- Gatekeeper phân loại sai → model phù hợp bị chọn sai → output kém

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Structured output schemas**: Mỗi agent yêu cầu JSON output theo schema cụ thể, validate trước khi xử lý | P0 | Planned |
| 2 | **Temperature settings**: Code generation dùng `temperature=0.1`, review dùng `temperature=0.3`, planning dùng `temperature=0.5` | P0 | Planned |
| 3 | **Multiple verification layers**: Lint → Test → Auditor review, mỗi layer catch lỗi layer trước bỏ sót | P0 | In Design |
| 4 | **Iterative prompt engineering**: Collection failure patterns, refine prompts dựa trên feedback | P1 | Planned |
| 5 | **Fallback to ESCALATED**: Khi retry count > 2, tự động chuyển sang Mentor hoặc human review | P0 | Implemented |
| 6 | **Prompt template versioning**: A/B test prompts, track success rate per template version | P2 | Planned |

**Contingency:**

- Nếu LLM quality quá thấp cho code generation:
  1. Reduce task scope — smaller modules, simpler implementations
  2. Add human-in-the-loop checkpoint sau IMPLEMENTING state
  3. Use template-based generation cho common patterns trước khi dùng LLM
  4. Consider fine-tuning model cho specific task types

---

### Risk #2: LLM API Outage

| Attribute | Detail |
|-----------|--------|
| **Category** | Technical |
| **Probability** | Medium (3) |
| **Impact** | Critical (4) |
| **Risk Score** | 12 — **CRITICAL** |
| **Description** | LLM provider (DeepSeek, Qwen) trải qua downtime, rate limiting, hoặc degraded performance. Khi primary provider down, hệ thống không thể process tasks. |

**Impact Analysis:**

- Tất cả agent operations dừng — không thể classify, plan, implement, review
- Tasks stuck ở current state, không thể transition
- User experience degraded — không có feedback, không có progress
- Nếu outage kéo dài: tasks queue buildup, cost spike khi resume

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Circuit Breaker Pattern**: Tự động chuyển sang fallback provider khi primary fail (xem `llm-integration.md` §2.3) | P0 | Implemented |
| 2 | **Fallback chain**: Mỗi agent có 2-3 fallback models (DeepSeek → Qwen → next) | P0 | Implemented |
| 3 | **Exponential backoff**: Retry với 1s, 2s, 4s delay trước khi fallback | P0 | Implemented |
| 4 | **Health checks**: Periodic ping mỗi provider, track availability metrics | P1 | Planned |
| 5 | **Graceful degradation**: Khi tất cả providers down, queue tasks, return 503, alert team | P0 | In Design |
| 6 | **Provider diversity**: Ít nhất 2 providers với different infrastructure (DeepSeek + Qwen) | P0 | Implemented |

**Contingency:**

- Nếu tất cả providers down:
  1. Return HTTP 503 cho new task submissions
  2. Queue existing tasks ở current state (không retry)
  3. Alert team qua Slack + Email
  4. Khi provider resume: process queued tasks theo priority
  5. Estimate: dựa trên historical outage data, 99% outages resolved trong <1 hour

---

### Risk #3: Cost Overrun

| Attribute | Detail |
|-----------|--------|
| **Category** | Financial |
| **Probability** | Medium (3) |
| **Impact** | High (3) |
| **Risk Score** | 9 — **HIGH** |
| **Description** | LLM API costs vượt budget dự kiến. Nguyên nhân: retry loops, complex tasks requiring nhiều LLM calls, context window large, hoặc provider price changes. |

**Impact Analysis:**

- Budget bị vượt nhanh — đặc biệt với Qwen 3.6 Plus ($2.40/1M output tokens)
- Cost tracking không theo kịp real-time spending
- Project có thể "cháy" budget trong vài ngày nếu không control
- Complex tasks với nhiều retries có thể tốn $5-10 per task

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Cost tracking from day 1**: Mọi LLM call log vào `llm_call_logs` và aggregated vào `cost_tracking` | P0 | Implemented |
| 2 | **Per-project cost limits**: WARNING > $5/day, CRITICAL > $20/day, BLOCKED > $50/day | P0 | In Design |
| 3 | **Model routing**: Simple tasks → cheap models (DeepSeek V4 Flash), Complex → expensive only when needed | P0 | Implemented |
| 4 | **Agent budgets**: Daily budget per agent type (xem `llm-observability.md` §7) | P1 | Planned |
| 5 | **Alerting**: Cost spike alert qua Slack + Email | P0 | Planned |
| 6 | **Daily/weekly cost reports**: Automated reports cho team | P2 | Planned |

**Cost Estimation (per task type):**

| Task Type | Avg LLM Calls | Avg Tokens | Est. Cost USD |
|-----------|---------------|------------|---------------|
| Simple (CRUD) | 3-5 | 10K-30K | $0.02 - $0.10 |
| Standard (Feature) | 8-15 | 50K-150K | $0.10 - $0.50 |
| Complex (Architecture) | 15-30 | 200K-500K | $0.50 - $3.00 |

**Contingency:**

- Nếu cost vượt $50/day/project:
  1. Auto-block tất cả LLM calls cho project đó
  2. Require manual approval để resume
  3. Review task queue và reduce complexity
  4. Switch tất cả agents sang cheaper models

---

### Risk #4: Context Window Overflow

| Attribute | Detail |
|---|---|
| **Category** | Technical |
| **Probability** | Low (2) |
| **Impact** | Medium (2) |
| **Risk Score** | 4 — **MEDIUM** (reduced from 6) |
| **Description** | LLM context window bị vượt khi build context cho complex modules. Task description + module spec + existing code + architectural laws + memory có thể vượt model context limit. "Lost in the Middle" phenomenon: LLM bỏ qua thông tin quan trọng ở giữa context. |

**Impact Analysis:**

- Context bị truncate → mất thông tin quan trọng → output kém
- Model tự động truncate (không kiểm soát) → hallucination
- "Lost in the Middle": thông tin quan trọng ở giữa context bị bỏ qua
- Task không thể process nếu context quá lớn, kể cả sau khi summarize

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|---|---|---|
| 1 | **ContextBuilder với priority-based truncation**: Task description (P100) > Output format (P90) > System prompt (P80) > Memory (P50) > Modules (P40) > Laws (P30) | P0 | ✅ Implemented |
| 2 | **"Lost in the Middle" mitigation**: Critical info at BEGINNING (P≥80) and END (P<40), less critical in MIDDLE (P40-79) | P0 | ✅ Implemented |
| 3 | **Token counting trước khi gửi**: Count tokens, truncate nếu vượt effective limit | P0 | ✅ Implemented |
| 4 | **Smart context selection**: Embedding search chỉ lấy relevant portions, không load toàn bộ | P1 | Phase 6 |
| 5 | **Model upgrade khi overflow**: Tự động chuyển sang model có context limit lớn hơn | P1 | Planned |
| 6 | **Task description summarization**: Dùng fast model để summarize task description nếu quá dài | P1 | Planned |
| 7 | **Context overflow protocol**: Escalate cho user nếu task quá lớn kể cả sau summarize | P2 | Planned |

**Contingency:**

- Nếu context overflow vẫn xảy ra sau tất cả mitigations:
  1. Escalate task — yêu cầu user chia nhỏ task
  2. Force switch sang Qwen 3.6 Plus (256K context)
  3. Reduce context — chỉ load task description + essential info
  4. Log overflow event và track pattern

---

### Risk #5: State Machine Edge Cases

| Attribute | Detail |
|---|---|
| **Category** | Technical |
| **Probability** | Low (2) |
| **Impact** | Critical (4) |
| **Risk Score** | 8 — **HIGH** (reduced from 12) |
| **Description** | 22 valid transitions và nhiều invalid transitions có nhiều edge cases—race conditions, stuck states, unexpected transition sequences. |

**Impact Analysis:**

- Task stuck ở một state không thể progress → workflow block
- Invalid transition không bị catch → data corruption
- Race condition khi concurrent transitions → inconsistent state
- Audit log incomplete → không thể trace issues

**Known Edge Cases:**

1. **Concurrent transitions**: Hai agents cố transition same task cùng lúc
2. **Zombie tasks**: Task stuck ở non-terminal state quá lâu (30+ minutes)
3. **Orphaned transitions**: Transition được ghi nhưng task state không update
4. **Retry confusion**: Task retry từ REVIEWING → IMPLEMENTING nhưng context đã thay đổi
5. **Circular dependencies**: Task A depends on Task B, Task B depends on Task A

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|---|---|---|
| 1 | **Optimistic locking**: `version` column + `SELECT FOR UPDATE` khi transition task, đảm bảo atomic | P0 | ✅ Implemented |
| 2 | **Retry on conflict**: `@retry_on_conflict` decorator với exponential backoff (0.1s → 0.2s → 0.4s) | P0 | ✅ Implemented |
| 3 | **Stuck task detection**: Background job detect tasks stuck >30 phút, auto-alert | P0 | ✅ Implemented |
| 4 | **Auto-escalation**: Tasks stuck >60 phút auto-escalate to ESCALATED | P0 | ✅ Implemented |
| 5 | **Comprehensive unit tests**: Test tất cả 22 valid transitions và invalid transitions | P0 | Planned |
| 6 | **Database constraints**: CHECK constraints cho valid state values | P0 | In Design |
| 7 | **Audit log integrity**: Hash chain validation, append-only audit logs | P0 | Planned |
| 8 | **Integration tests cho concurrent transitions**: Verify chỉ 1 transition thành công | P0 | Planned |

**Contingency:**

- Nếu phát hiện stuck task:
  1. Alert team qua Slack
  2. Admin use force transition API để manually move task
  3. Review audit logs để trace root cause
  4. Add specific constraint hoặc fix transition logic

---

### Risk #6: Security Vulnerability

| Attribute | Detail |
|-----------|--------|
| **Category** | Security |
| **Probability** | Low (2) |
| **Impact** | Critical (4) |
| **Risk Score** | 8 — **HIGH** |
| **Description** | Bảo mật bị vi phạm: LLM prompt injection, API key exposure, SQL injection, XSS, hoặc unauthorized access. Đặc biệt rủi ro với LLM-based systems: prompt injection có thể khiến agent thực hiện actions ngoài ý muốn. |

**Impact Analysis:**

- **Prompt injection**: Attacker inject malicious instructions vào task description, agent thực hiện unintended actions
- **API key leak**: LLM API keys lộ trong logs, source code, hoặc responses
- **SQL injection**: Dù dùng SQLAlchemy ORM, vẫn có risk nếu dùng raw queries
- **XSS**: Cross-site scripting qua task descriptions hiển thị trong dashboard
- **Unauthorized access**: RBAC misconfiguration cho phép user thực hiện privileged actions

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Input validation**: Pydantic models với `max_length`, regex pattern, HTML stripping cho tất cả input | P0 | In Design |
| 2 | **Prompt injection defense**: System prompts với clear boundaries, input sanitization, output validation | P0 | Planned |
| 3 | **API key security**: Keys chỉ lưu hash (SHA-256), raw key trả 1 lần, env vars only (LAW-005) | P0 | In Design |
| 4 | **SQL injection prevention**: SQLAlchemy ORM only, parameterized queries, no raw SQL | P0 | Planned |
| 5 | **XSS prevention**: Output sanitization, Content-Security-Policy headers | P1 | Planned |
| 6 | **RBAC enforcement**: Permission checks trên mỗi endpoint, test coverage | P0 | Planned |
| 7 | **Agent permission boundaries**: Mỗi agent chỉ có quyền trong scope (xem `security-design.md` §6) | P0 | In Design |
| 8 | **Secret scanning**: Pre-commit hooks, CI pipeline checks (truffleHog, gitleaks) | P1 | Planned |
| 9 | **Rate limiting**: Per-role, per-agent rate limits (xem `security-design.md` §3.1) | P1 | Planned |

**Contingency:**

- Nếu security breach:
  1. Immediately revoke compromised API keys
  2. Rotate JWT secret keys
  3. Review all audit logs for unauthorized access
  4. Patch vulnerability
  5. Notify affected users
  6. Post-incident review

---

### Risk #7: Database Performance

| Attribute | Detail |
|-----------|--------|
| **Category** | Technical |
| **Probability** | Medium (3) |
| **Impact** | Medium (2) |
| **Risk Score** | 6 — **MEDIUM** |
| **Description** | Database performance degradation khi data volume tăng: slow queries, connection pool exhaustion, lock contention, especially trên tasks và audit_logs tables. |

**Impact Analysis:**

- State transition latency tăng >100ms → workflow slowed
- List queries timeout → dashboard không load
- Full table scans → high CPU usage → cascading failures
- Connection pool exhaustion → API 503

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Proper indexing**: Composite indexes cho common queries, partial indexes cho filtered queries | P0 | Planned |
| 2 | **Connection pooling**: SQLAlchemy pool_size=20, max_overflow=10 | P0 | Planned |
| 3 | **Read replicas**: Separate read replicas cho GET endpoints và reports | P1 | Phase 7 |
| 4 | **Query optimization**: EXPLAIN ANALYZE cho slow queries, N+1 query prevention | P0 | Planned |
| 5 | **Table partitioning**: Partition audit_logs và llm_call_logs by date | P2 | Planned |
| 6 | **Data archival**: Move old data (audit_logs > 1 year, llm_call_logs > 90 days) to cold storage | P1 | Planned |
| 7 | **Database monitoring**: Slow query logging, connection pool metrics, disk usage alerts | P1 | Planned |

**Performance Targets:**

| Query Type | Target | Max |
|-----------|--------|-----|
| Single row by PK | < 1ms | 5ms |
| Indexed query with filter | < 5ms | 10ms |
| Paginated list (20 rows) | < 20ms | 50ms |
| Aggregate query | < 200ms | 500ms |
| State transition (with lock) | < 50ms | 100ms |

**Contingency:**

- Nếu database vẫn slow sau mitigations:
  1. Add read replica để offload read queries
  2. Increase connection pool size
  3. Add Redis caching cho hot queries (project stats, task counts)
  4. Consider database upgrade (vertical scaling)

---

### Risk #8: Agent Coordination Failure

| Attribute | Detail |
|-----------|--------|
| **Category** | Operational |
| **Probability** | Medium (3) |
| **Impact** | High (3) |
| **Risk Score** | 9 — **HIGH** |
| **Description** | Agents không điều phối được với nhau: Orchestrator tạo plan kém, Specialist không hiểu spec, Auditor và Specialist không đồng nhất về quality standards. Workflow bị stuck hoặc produce low-quality output. |

**Impact Analysis:**

- Orchestrator chia task không rõ ràng → Specialist implement sai
- Specialist và Auditor không aligned → endless REVIEWING → IMPLEMENTING loop
- Context không được pass đầy đủ giữa agents → mỗi agent làm việc với incomplete info
- Agent outputs không compatible → integration issues

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Structured output schemas**: Mỗi agent produces output theo JSON schema cụ thể, validated trước khi pass cho agent tiếp theo | P0 | In Design |
| 2 | **Context passing protocol**: Orchestrator builds context cho Specialist, Specialist passes output + context cho Auditor | P0 | Planned |
| 3 | **Retry limit**: Max 2 retries, sau đó ESCALATE cho Mentor | P0 | Implemented |
| 4 | **Escalation protocol**: Mentor takeover khi coordination fail, produces final verdict | P1 | Phase 5 |
| 5 | **Shared architectural laws**: Tất cả agents reference same architectural laws (LAW-001 to LAW-020) | P0 | In Design |
| 6 | **Human-in-the-loop**: ESCALATED state cho phép human intervention | P0 | Implemented |

**Contingency:**

- Nếu agent coordination fail thường xuyên:
  1. Review prompt templates — refine based on failure patterns
  2. Add intermediate validation steps
  3. Increase context passed between agents
  4. Consider simplifying workflow (fewer states, fewer agents)

---

### Risk #9: Dependency Management Complexity

| Attribute | Detail |
|-----------|--------|
| **Category** | Technical |
| **Probability** | Low (2) |
| **Impact** | Medium (2) |
| **Risk Score** | 4 — **MEDIUM** |
| **Description** | Hệ thống có nhiều dependencies: LLM providers (DeepSeek, Qwen), PostgreSQL, pgvector, và có thể Redis. Quản lý versions, compatibility, và updates là complex. |

**Impact Analysis:**

- Provider API changes breaking existing integration
- PostgreSQL extension (pgvector) version incompatibility
- Python package dependency conflicts
- SQLAlchemy version changes breaking migrations

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Provider abstraction layer**: LLM Gateway abstracts provider-specific APIs, easier to swap | P0 | In Design |
| 2 | **Pin dependency versions**: requirements.txt với exact versions,定期 review và update | P0 | Planned |
| 3 | **Integration tests**: Test mỗi provider integration riêng biệt | P1 | Planned |
| 4 | **API versioning**: Use provider API versions explicitly, not "latest" | P1 | Planned |
| 5 | **Dependency vulnerability scanning**: CI pipeline scans cho known vulnerabilities | P1 | Planned |

**Contingency:**

- Nếu provider API breaking change:
  1. Fallback to previous API version (if available)
  2. Update adapter layer to support new API
  3. Switch to alternative provider temporarily
  4. Pin to stable version until fix available

---

### Risk #10: OpenCode Integration Failure

| Attribute | Detail |
|-----------|--------|
| **Category** | Operational |
| **Probability** | Low (2) |
| **Impact** | Critical (4) |
| **Risk Score** | 8 — **HIGH** |
| **Description** | MVP phụ thuộc hoàn toàn vào OpenCode cho execution layer. Nếu OpenCode crash, có compatibility issues, hoặc rate limits, agents không thể hoạt động. |

**Impact Analysis:**

- OpenCode down → tất cả agent operations dừng
- OpenCode API changes → agent integration breaks
- OpenCode rate limits → agents bị throttled
- OpenCode security vulnerability → agents có thể bị compromise

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|-----------|----------|--------|
| 1 | **Health checks**: Periodic ping OpenCode trước mỗi agent call | P0 | Planned |
| 2 | **Timeout handling**: Every OpenCode call có timeout, fallback nếu timeout | P0 | Planned |
| 3 | **Graceful degradation**: Nếu OpenCode unreachable, task chuyển sang ESCALATED | P0 | Planned |
| 4 | **OpenCode version pinning**: Pin to stable OpenCode version, controlled updates | P1 | Planned |
| 5 | **Command allowlist**: Restrict commands agents có thể execute qua OpenCode (xem `security-design.md` §7.2) | P0 | In Design |
| 6 | **Monitoring**: Track OpenCode call success rate, latency, error rate | P1 | Planned |

**Contingency:**

- Nếu OpenCode unavailable:
  1. Tasks auto-transition to BLOCKED state
  2. Alert team via Slack + Email
  3. When OpenCode resumes, automatically process queued tasks
  4. Long-term: evaluate building custom tool system (Phase 8+)

---

### Risk #11: Dependency Blocked (NEW v4.1)

| Attribute | Detail |
|---|---|
| **Category** | Operational |
| **Probability** | Medium (3) |
| **Impact** | High (3) |
| **Risk Score** | 9 — **HIGH** |
| **Description** | BLOCKED state trở thành "hố đen" — task bị chặn vì dependency chưa xong hoặc thiếu thông tin, nhưng không có cơ chế tự động nhắc nhở user. Nếu dependency không bao giờ resolved, task chết yểu ở BLOCKED state. |

**Impact Analysis:**

- Task stuck ở BLOCKED vô hạn → workflow block
- User không được thông báo → không biết cần cung cấp thông tin
- Dependency chain bị block → cascade effect, nhiều tasks bị ảnh hưởng
- Không có escalation path từ BLOCKED → Mentor

**Mitigations:**

| # | Mitigation | Priority | Status |
|---|---|---|---|
| 1 | **BLOCKED timeout mechanism**: Auto-escalate BLOCKED → ESCALATED sau 120 phút | P0 | ✅ Implemented |
| 2 | **Human-in-the-loop notifications**: Auto-send notification khi task enters BLOCKED | P0 | ✅ Implemented |
| 3 | **Warning notification**: HIGH priority alert sau 60 phút BLOCKED | P0 | ✅ Implemented |
| 4 | **Notification channels**: Dashboard (WebSocket), Slack, Email, Webhook | P0 | ✅ Implemented |
| 5 | **BLOCKED → ESCALATED transition**: New valid transition trong state machine | P0 | ✅ Implemented |
| 6 | **Notification database**: Store notifications trong `notifications` table cho audit | P0 | ✅ Implemented |
| 7 | **Auto-escalation with reason**: Mentor nhận full context khi BLOCKED task escalated | P0 | ✅ Implemented |

**Contingency:**

- Nếu BLOCKED task vẫn không resolved sau escalation:
  1. Mentor reviews và quyết định: cancel task hoặc create new plan
  2. Nếu user không respond trong 24h → auto-cancel task
  3. Log pattern để cải thiện dependency detection trong tương lai

---

## 3. Risk Matrix Summary

### 3.1 Risk Matrix Visualization

```
Impact →    Low (1)            Medium (2)           High (3)             Critical (4)
          ┌─────────────┬─────────────────┬─────────────────┬──────────────────────┐
High (4)  │             │                 │                 │ #1 LLM Quality      │
          │             │                 │                 │    (4×3=12) ★       │
          │             │                 │                 │ #2 LLM Outage       │
          │             │                 │                 │    (3×4=12) ★        │
          ├─────────────┼─────────────────┼─────────────────┼──────────────────────┤
Med  (3)  │             │                 │ #3 Cost Overrun  │ #5 State Machine     │
          │             │                 │    (3×2=6)       │    (3×4=12) ★        │
          │             │                 │ #7 DB Perf       │                      │
          │             │                 │    (3×2=6)       │                      │
          │             │                 │ #8 Coordination  │                      │
          │             │                 │    (3×3=9) ●     │                      │
          ├─────────────┼─────────────────┼─────────────────┼──────────────────────┤
Low  (2)  │             │ #9 Dependencies │ #6 Security      │ #10 OpenCode         │
          │             │    (2×2=4)       │    (2×4=8) ●     │    (2×4=8) ●         │
          ├─────────────┼─────────────────┼─────────────────┼──────────────────────┤
VLow (1)  │    #4       │                 │                 │                      │
          │ Context     │                 │                 │                      │
          │ Overflow    │                 │                 │                      │
          │ (1×3=3)     │                 │                 │                      │
          └─────────────┴─────────────────┴─────────────────┴──────────────────────┘

Legend: ★ = Critical (10-16), ● = High (8-9), ▲ = Medium (4-6), ○ = Low (1-3)
```

Wait, #4 should be Probability Medium (3) × Impact Medium (2) = 6, not (1×3). Let me fix:

Actually, re-reading my own assessment:
- #4: Probability Medium (3), Impact Medium (2) = 6 — MEDIUM
- Let me redo the matrix with correct values

```
Impact →    Low (1)            Medium (2)           High (3)             Critical (4)
          ┌─────────────┬─────────────────┬─────────────────┬──────────────────────┐
High (4)  │             │                 │                 │ #1 LLM Quality       │
          │             │                 │                 │    (4×3=12) ★        │
          ├─────────────┼─────────────────┼─────────────────┼──────────────────────┤
Medium(3)  │             │ #7 DB Perf (6)  │ #3 Cost Overrun │ #2 LLM Outage       │
          │             │                 │    (3×3=9) ●     │    (3×4=12) ★        │
          │             │                 │ #8 Coordination │ #5 State Machine     │
          │             │                 │    (3×3=9) ●     │    (3×4=12) ★        │
          │             │ #4 Context (6)  │                 │                      │
          ├─────────────┼─────────────────┼─────────────────┼──────────────────────┤
Low  (2)  │             │ #9 Deps (4)     │                 │ #6 Security (8) ●    │
          │             │                 │                 │ #10 OpenCode (8) ●   │
          └─────────────┴─────────────────┴─────────────────┴──────────────────────┘

Legend: ★ = Critical (12-16), ● = High (8-9), ▲ = Medium (4-6), ○ = Low (1-3)
```

### 3.2 Risk Priority Ranking

| Rank | Risk | Score | Category | Priority |
|---|---|---|---|---|
| 1 | LLM Quality Inconsistency | 12 | Technical | CRITICAL |
| 2 | LLM API Outage | 12 | Technical | CRITICAL |
| 3 | Agent Coordination Failure | 9 | Operational | HIGH |
| 4 | Dependency Blocked (NEW v4.1) | 9 | Operational | HIGH |
| 5 | State Machine Edge Cases | 8 | Technical | HIGH (reduced from 12) |
| 6 | Security Vulnerability | 8 | Security | HIGH |
| 7 | OpenCode Integration Failure | 8 | Operational | HIGH |
| 8 | Cost Overrun | 6 | Financial | MEDIUM |
| 9 | Context Window Overflow | 4 | Technical | MEDIUM (reduced from 6) |
| 10 | Database Performance | 6 | Technical | MEDIUM |
| 11 | Dependency Management | 4 | Technical | MEDIUM |

---

## 4. Additional Risks (Lower Priority)

### 4.1 Operational Risks

| Risk | Probability | Impact | Score | Mitigation |
|------|------------|--------|-------|-----------|
| **Team knowledge gap**: Team chưa quen với LLM-based system | Medium (3) | Low (1) | 3 | Training, documentation, pair programming |
| **Infrastructure failure**: Server crash, network issues | Low (2) | Medium (2) | 4 | Multi-AZ deployment, automated failover |
| **Data loss**: Database corruption hoặc accidental deletion | Very Low (1) | Critical (4) | 4 | Automated backups, disaster recovery plan |

### 4.2 Financial Risks

| Risk | Probability | Impact | Score | Mitigation |
|------|------------|--------|-------|-----------|
| **Provider price increase**: LLM API costs tăng | Medium (3) | Medium (2) | 6 | Multi-provider strategy, negotiate contracts |
| **Budget underestimation**: Actual costs higher than estimated | Medium (3) | Medium (2) | 6 | Cost tracking from day 1, per-project limits |
| **Resource over-provisioning**: Server costs higher than needed | Low (2) | Low (1) | 2 | Start small, scale based on metrics |

### 4.3 Security Risks (Additional)

| Risk | Probability | Impact | Score | Mitigation |
|------|------------|--------|-------|-----------|
| **DDoS attack**: API overwhelmed by malicious requests | Low (2) | Medium (2) | 4 | Rate limiting, WAF, CDN protection |
| **Insider threat**: Malicious user within organization | Very Low (1) | High (3) | 3 | Audit logs, RBAC, principle of least privilege |
| **Data breach**: Database access by unauthorized party | Very Low (1) | Critical (4) | 4 | Encryption at rest, TLS in transit, access controls |

---

## 5. Risk Monitoring and Review

### 5.1 Monitoring Cadence

| Activity | Frequency | Responsible | Output |
|----------|-----------|-------------|--------|
| Risk register review | Weekly | Tech Lead | Updated risk scores |
| LLM quality metrics review | Daily | Agent Engineer | Quality report |
| Cost budget review | Daily | Project Manager | Cost report |
| Security scan | Weekly | Security Engineer | Vulnerability report |
| Dependency vulnerability scan | Weekly | DevOps Engineer | Dependency report |
| Performance benchmark | Weekly | Backend Engineer | Performance report |
| Full risk assessment | Monthly | Team | Comprehensive review |

### 5.2 Risk Indicators

| Indicator | Metric | Warning Threshold | Critical Threshold | Source |
|-----------|--------|--------------------|-------------------|--------|
| LLM quality | Task success rate (reach DONE) | < 70% | < 50% | Task state stats |
| LLM availability | Provider success rate | < 98% | < 95% | LLM call logs |
| Cost trend | Daily cost per project | > $5/project/day | > $20/project/day | Cost tracking |
| Cost forecast | Monthly cost projection | > 80% of budget | > 100% of budget | Cost tracking |
| State machine health | Tasks stuck > 30 min | > 5 tasks | > 10 tasks | Task monitoring |
| Security incidents | Auth failures per hour | > 50 | > 200 | Auth logs |
| Database performance | Avg query latency | > 100ms | > 500ms | DB metrics |
| Agent coordination | Review-implement loop count | > 2 (approaching max) | > 2 (at max) | Task retry count |
| OpenCode health | Call success rate | < 98% | < 95% | OpenCode metrics |
| Context overflow | Overflow events per day | > 5 | > 20 | LLM call logs |

### 5.3 Escalation Protocol

```
Risk Detected → Assess Severity → Escalate:

■ CRITICAL (Score 12-16):
  → Immediate Slack alert to #critical-risks
  → Tech Lead notified within 15 minutes
  → War room convened within 1 hour
  → Status page updated
  → Resolution plan within 4 hours

■ HIGH (Score 8-9):
  → Slack alert to #team-alerts
  → Team notified within 2 hours
  → Resolution plan within 24 hours
  → Post-incident review within 48 hours

■ MEDIUM (Score 4-6):
  → Dashboard notification
  → Discussed in daily standup
  → Resolution within 1 week
  → Reviewed in weekly risk review

■ LOW (Score 1-3):
  → Logged in risk register
  → Monitored passively
  → Reviewed in monthly risk assessment
```

### 5.4 Risk Review Template

```markdown
## Monthly Risk Review - [Month Year]

### Risk Register Updates
| ID | Risk | Previous Score | Current Score | Trend | Notes |
|----|------|---------------|--------------|-------|-------|
| R1 | LLM Quality | 12 | 10 | ↓ | Prompt improvements reducing failures |
| R2 | LLM Outage | 12 | 12 | → | No change, circuit breaker working |
| ... |

### New Risks Identified
1. [Risk description] - [Score] - [Mitigation plan]

### Risks Retired
1. [Risk that no longer applies] - [Reason]

### Action Items
1. [Action] - [Owner] - [Due date]
2. [Action] - [Owner] - [Due date]

### Key Metrics
- Task success rate: XX%
- Average daily cost: $XX
- LLM availability: XX%
- Mean time to resolution: XX hours
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Review schedule: Monthly*
*Maintained by: AI SDLC System Architecture Team*