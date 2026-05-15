# Error Handling & Resilience Design

> Tài liệu thiết kế xử lý lỗi và khả năng phục hồi cho AI SDLC System

---

## 1. Error Handling Philosophy

### 1.1 Nguyên tắc cốt lõi

Hệ thống tuân thủ 4 nguyên tắc không ngoại lệ:

| # | Nguyên tắc | Mô tả |
|---|-----------|--------|
| 1 | **Never silent failures** | Mọi lỗi phải được ghi nhận, không bao giờ im lặng bỏ qua. Một lỗi không được log chính là bug |
| 2 | **Always log with context (LAW-006)** | Mỗi log entry phải kèm theo full context: agent_id, workflow_id, node_type, model, input summary, output summary |
| 3 | **Circuit breaker for external calls** | Mọi gọi ra bên ngoài (LLM, API, database) phải được bảo vệ bởi circuit breaker |
| 4 | **Graceful degradation** | Khi một component fail, hệ thống phải tiếp tục hoạt động với chức năng giảm thiểu, không crash toàn bộ |

### 1.2 Phân loại lỗi

```
┌─────────────────────────────────────────────────┐
│                   Errors                         │
├─────────────┬──────────────┬────────────────────┤
│   Agent      │   System     │      LLM          │
│   Errors     │   Errors     │      Errors        │
├─────────────┼──────────────┼────────────────────┤
│ Logic error  │ DB down      │ Timeout            │
│幻觉 Halluc.  │ Network fail │ Rate limit         │
│ Bad output   │ Config error │ Context exceeded   │
│ Task timeout │ File I/O     │ Auth failed        │
│ Validation   │ Memory OOM   │ Server error       │
└─────────────┴──────────────┴────────────────────┘
```

### 1.3 Nguyên tắc xử lý theo loại lỗi

- **Transient errors** (tạm thời): Retry với exponential backoff → circuit breaker → fallback model
- **Permanent errors** (vĩnh viễn): Log → transition sang FAILED state → notify → escalated to human
- **Agent errors**: Log với full context → retry (max 2 lần task) → fallback behavior
- **System errors**: Log → alert → circuit breaker → graceful degradation
- **LLM errors**: Retry → circuit breaker → fallback model → escalate

---

## 2. Circuit Breaker Design

### 2.1 State Machine

Circuit breaker vận hành theo pattern 3 trạng thái chuẩn:

```
                    Failure threshold reached
                    (5 consecutive failures)
    ┌─────────┐  ──────────────────────────────►  ┌─────────┐
    │  CLOSED  │                                  │  OPEN    │
    └─────────┘  ◄──────────────────────────────  └─────────┘
         ▲          Recovery timeout elapsed            │
         │             (30-90s per model)               │
         │                                                │
         │          ┌─────────┐                          │
         │          │HALF-OPEN│ ◄────────────────────────┘
         │          └─────────┘    Recovery timeout elapsed
         │                │
         │    ┌───────────┴───────────┐
         │    │                       │
         │  Success                  Failure
         │  (test call)             (test call)
         │    │                       │
         └────┘                       └────────► BACK TO OPEN
```

### 2.2 Ba trạng thái chi tiết

#### CLOSED (Bình thường)
- Mọi request được forwarded bình thường đến LLM provider
- Đếm số consecutive failures
- Khi đạt **5 consecutive failures** → chuyển sang **OPEN**
- Mỗi successful call reset failure count về 0

#### OPEN (Chờ)
- **Tất cả requests bị reject ngay lập tức** (fail fast)
- Không gọi LLM provider để tránh cascading failure
- Trigger **fallback model** cho mọi request
- Chờ **recovery timeout** (30-90s) trước khi chuyển sang **HALF-OPEN**

#### HALF-OPEN (Thử nghiệm)
- Cho phép **tối đa 3 test calls** đến LLM provider
- Nếu **tất cả 3 test calls thành công** → chuyển về **CLOSED**
- Nếu **bất kỳ test call nào thất bại** → chuyển ngược về **OPEN**
- Reset lại recovery timeout

### 2.3 Per-Model Circuit Breaker

Mỗi model có circuit breaker riêng biệt:

```python
CIRCUIT_BREAKER_CONFIG = {
    "deepseek-v4-flash": {
        "failure_threshold": 5,
        "recovery_timeout": 30,    # seconds
        "half_open_max_calls": 3,
    },
    "deepseek-v4-pro": {
        "failure_threshold": 5,
        "recovery_timeout": 60,    # seconds
        "half_open_max_calls": 3,
    },
    "qwen-3.6-plus": {
        "failure_threshold": 5,
        "recovery_timeout": 90,    # seconds
        "half_open_max_calls": 3,
    },
    "qwen-3.5-plus": {
        "failure_threshold": 5,
        "recovery_timeout": 60,    # seconds
        "half_open_max_calls": 3,
    },
}
```

### 2.4 Circuit Breaker State Persistence

Circuit breaker state được lưu trong database để đảm bảo persistence across restarts:

```sql
CREATE TABLE circuit_breaker_state (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model           VARCHAR(100) NOT NULL UNIQUE,
    state           VARCHAR(20) NOT NULL DEFAULT 'CLOSED',  -- CLOSED, OPEN, HALF_OPEN
    failure_count   INTEGER NOT NULL DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    half_open_calls INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_state CHECK (state IN ('CLOSED', 'OPEN', 'HALF_OPEN'))
);

CREATE INDEX idx_circuit_breaker_model ON circuit_breaker_state(model);
```

### 2.5 Fallback Behavior khi Circuit OPEN

```
Request arrives
      │
      ▼
┌─────────────┐
│ Check circuit│
│   state      │
└──────┬──────┘
       │
   ┌───┴───────────────┐
   │                   │
 CLOSED              OPEN/HALF-OPEN
   │                   │
   ▼                   ▼
 Forward to       Use fallback model
 primary model    (see Section 7)
```

---

## 3. Retry with Exponential Backoff

### 3.1 Retry Configuration

Phân biệt rõ 2 loại retry:

| Loại Retry | Max Retries | Mục đích |
|-----------|-------------|----------|
| **LLM Call Retry** | 3 | Retry khi gọi LLM provider thất bại (per API call) |
| **Task Retry** | 2 | Retry toàn bộ task khi agent execution thất bại (per workflow node) |

### 3.2 LLM Call Retry Logic

```python
LLM_RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1,          # seconds
    "backoff_multiplier": 2,   # 1s → 2s → 4s
    "max_delay": 10,           # seconds (cap)
    "jitter": True,            # random jitter ±200ms để tránh thundering herd
}

# Retry timeline:
# Attempt 1: immediate
# Attempt 2: wait 1s  (±200ms jitter)
# Attempt 3: wait 2s  (±200ms jitter)
# Attempt 4: wait 4s  (±200ms jitter) — nếu vẫn fail → circuit breaker count +1
```

### 3.3 Retryable vs Non-Retryable Errors

#### Retryable Errors (có thể thử lại)

| Error Type | HTTP Code | Lý do retry |
|-----------|-----------|-------------|
| `timeout` | 408 / 504 | Network hoặc server tạm thời quá tải |
| `rate_limit` | 429 | Provider rate limit, cần chờ reset |
| `server_error` | 500 / 502 / 503 | Lỗi tạm thời từ provider |

#### Non-Retryable Errors (không thể thử lại - fail ngay lập tức)

| Error Type | HTTP Code | Lý do không retry |
|-----------|-----------|-------------------|
| `auth_failed` | 401 / 403 | API key không hợp lệ, retry vô nghĩa |
| `invalid_request` | 400 | Request malformed, retry sẽ cho cùng kết quả |
| `context_length_exceeded` | 400 | Input quá dài, cần thay đổi prompt không phải retry |

### 3.4 Retry Implementation Pseudocode

```python
async def call_llm_with_retry(model: str, prompt: str, config: dict) -> LLMResponse:
    circuit_breaker = get_circuit_breaker(model)

    # Check circuit breaker state first
    if circuit_breaker.state == "OPEN":
        logger.warning(f"Circuit OPEN for {model}, using fallback")
        return await call_fallback_model(model, prompt, config)

    last_error = None
    for attempt in range(config["max_retries"] + 1):
        try:
            response = await call_llm(model, prompt, config)
            circuit_breaker.record_success()
            return response
        except RetryableError as e:
            last_error = e
            if attempt < config["max_retries"]:
                delay = calculate_backoff(attempt, config)
                logger.info(f"Retry {model} attempt {attempt+1}/{config['max_retries']}, "
                          f"waiting {delay}s. Error: {e.error_type}")
                await asyncio.sleep(delay)
            else:
                circuit_breaker.record_failure()
                logger.error(f"All retries exhausted for {model}: {e}")
        except NonRetryableError as e:
            circuit_breaker.record_failure()
            logger.error(f"Non-retryable error for {model}: {e.error_type}")
            raise

    # All retries failed → try fallback model
    logger.warning(f"Falling back from {model} after {config['max_retries']+1} failures")
    return await call_fallback_model(model, prompt, config)
```

---

## 4. Rate Limiting

### 4.1 Multi-Level Rate Limiting

Hệ thống áp dụng rate limiting ở 3 tầng:

```
┌─────────────────────────────────────────┐
│           Rate Limiting Layers           │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │    Per-User Rate Limits          │    │
│  │  (configurable per user tier)    │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────────┐    │
│  │    Per-Agent Rate Limits         │    │
│  │  (limit per agent type)          │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────────┐    │
│  │    Per-Model Rate Limits         │    │
│  │  (respect provider limits)       │    │
│  └─────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

### 4.2 Per-User Rate Limits

```python
USER_RATE_LIMITS = {
    "free_tier": {
        "requests_per_minute": 10,
        "requests_per_day": 100,
        "concurrent_workflows": 1,
    },
    "pro_tier": {
        "requests_per_minute": 30,
        "requests_per_day": 500,
        "concurrent_workflows": 3,
    },
    "enterprise_tier": {
        "requests_per_minute": 100,
        "requests_per_day": 5000,
        "concurrent_workflows": 10,
    },
}
```

### 4.3 Per-Agent Rate Limits

```python
AGENT_RATE_LIMITS = {
    "coder": {
        "calls_per_minute": 15,
        "calls_per_hour": 200,
    },
    "reviewer": {
        "calls_per_minute": 10,
        "calls_per_hour": 150,
    },
    "mentor": {
        "calls_per_minute": 5,
        "calls_per_hour": 60,
    },
}
```

### 4.4 Per-Model Rate Limits (Provider Limits)

```python
MODEL_RATE_LIMITS = {
    "deepseek-v4-flash": {
        "rpm": 60,       # requests per minute (provider limit)
        "rpm_buffer": 5,  # keep 5 RPM below limit for safety
        "effective_rpm": 55,
    },
    "deepseek-v4-pro": {
        "rpm": 30,
        "rpm_buffer": 3,
        "effective_rpm": 27,
    },
    "qwen-3.6-plus": {
        "rpm": 60,
        "rpm_buffer": 5,
        "effective_rpm": 55,
    },
    "qwen-3.5-plus": {
        "rpm": 30,
        "rpm_buffer": 3,
        "effective_rpm": 27,
    },
}
```

### 4.5 Mentor Quota

Mentor có quota đặc biệt: **10 calls/day per user**, được enforce riêng qua database:

```sql
CREATE TABLE mentor_quota (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    call_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    call_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT mentor_quota_unique UNIQUE (user_id, call_date)
);

-- Check constraint: call_count không vượt quá 10
ALTER TABLE mentor_quota ADD CONSTRAINT mentor_quota_limit
    CHECK (call_count <= 10);
```

```python
async def check_mentor_quota(user_id: str) -> bool:
    """Return True if user still has mentor quota today"""
    quota = await db.fetch_one(
        "SELECT call_count FROM mentor_quota "
        "WHERE user_id = $1 AND call_date = CURRENT_DATE",
        user_id
    )
    if quota is None or quota["call_count"] < 10:
        return True
    return False

async def increment_mentor_quota(user_id: str) -> None:
    """Increment mentor call count for today"""
    await db.execute(
        "INSERT INTO mentor_quota (user_id, call_count) "
        "VALUES ($1, 1) "
        "ON CONFLICT (user_id, call_date) "
        "DO UPDATE SET call_count = mentor_quota.call_count + 1, "
        "updated_at = NOW()",
        user_id
    )
```

---

## 5. Timeout Handling

### 5.1 Timeout Hierarchy

```
┌───────────────────────────────────────────────────────┐
│                   Timeout Hierarchy                    │
├───────────────────────────────────────────────────────┤
│                                                       │
│  Workflow Level                                       │
│  └── Max total: 60 minutes                            │
│                                                       │
│      Node Level                                       │
│      ├── execute node: 10 minutes                      │
│      ├── verify node: 5 minutes                        │
│      └── review node: 5 minutes                       │
│                                                       │
│          LLM Call Level                               │
│          ├── deepseek-v4-flash: 30s                    │
│          ├── deepseek-v4-pro: 60s                      │
│          ├── qwen-3.6-plus: 90s                        │
│          └── qwen-3.5-plus: 60s                        │
│                                                       │
│              API Level                                 │
│              └── General API: 3 seconds (LAW-007)      │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 5.2 LLM Call Timeout

```python
LLM_TIMEOUT_CONFIG = {
    "deepseek-v4-flash": {
        "timeout": 30,   # seconds — flash model nhanh, timeout ngắn
        "streaming_timeout": 60,  # cho streaming responses
    },
    "deepseek-v4-pro": {
        "timeout": 60,   # seconds — pro model mất nhiều thời gian hơn
        "streaming_timeout": 120,
    },
    "qwen-3.6-plus": {
        "timeout": 90,   #_seconds — model lớn cần thời gian dài
        "streaming_timeout": 180,
    },
    "qwen-3.5-plus": {
        "timeout": 60,
        "streaming_timeout": 120,
    },
}
```

### 5.3 Workflow Node Timeout

```python
WORKFLOW_NODE_TIMEOUTS = {
    "execute": {
        "timeout": 600,       # 10 minutes
        "description": "Code execution, generation, refactoring",
    },
    "verify": {
        "timeout": 300,       # 5 minutes
        "description": "Test running, analysis, validation",
    },
    "review": {
        "timeout": 300,       # 5 minutes
        "description": "Code review, quality check",
    },
}
```

### 5.4 API Timeout

Theo **LAW-007**: mọi API response phải trả về trong vòng **3 giây**.

```python
API_TIMEOUT_CONFIG = {
    "general_api": {
        "timeout": 3,          # seconds (LAW-007)
        "description": "Tất cả API endpoints phải respond trong 3s",
    },
    "health_check": {
        "timeout": 1,          # seconds
        "description": "Health check phải nhanh",
    },
    "webhook": {
        "timeout": 5,          # seconds
        "description": "Webhook callbacks có thêm thời gian",
    },
}
```

### 5.5 Timeout Handling Flow

```
Timeout occurs
      │
      ▼
┌─────────────┐
│ Log error   │  — Include: model, node_type, duration, input_hash
│ with context │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Classify    │  — LLM timeout → retry then circuit breaker
│ timeout type │  — Node timeout → transition workflow state
└──────┬──────┘  — API timeout → return 504 to client
       │
       ▼
┌─────────────────┐
│ State Transition│
│                 │
│ LLM timeout:   │  → record failure in circuit breaker
│ Node timeout:  │  → BLOCKED / FAILED
│ API timeout:   │  → 504 Gateway Timeout
└─────────────────┘
```

---

## 6. Workflow Error Recovery

### 6.1 Workflow State Persistence

Workflow state được persist liên tục vào database để enable recovery:

```sql
CREATE TABLE workflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    project_id      UUID REFERENCES projects(id),
    current_node    VARCHAR(50) NOT NULL,
    state           VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- PENDING, RUNNING, BLOCKED, FAILED, COMPLETED, CANCELLED
    node_history     JSONB NOT NULL DEFAULT '[]',
    -- [{node, state, started_at, completed_at, error, output_hash}]
    context         JSONB NOT NULL DEFAULT '{}',
    -- Shared context giữa các nodes
    error_info      JSONB,
    -- {error_type, error_message, error_category, retry_count}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,

    CONSTRAINT valid_workflow_state
        CHECK (state IN ('PENDING', 'RUNNING', 'BLOCKED', 'FAILED', 'COMPLETED', 'CANCELLED'))
);

CREATE INDEX idx_workflows_user ON workflows(user_id);
CREATE INDEX idx_workflows_state ON workflows(state);
CREATE INDEX idx_workflows_project ON workflows(project_id);
```

### 6.2 Node History Tracking

Mỗi node execution được track chi tiết:

```python
NODE_HISTORY_ENTRY = {
    "node": "execute",                # node name
    "state": "COMPLETED",             # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    "started_at": "2026-05-14T10:00:00Z",
    "completed_at": "2026-05-14T10:08:30Z",
    "duration_ms": 510000,            # execution duration
    "error": None,                    # error details if failed
    "output_hash": "sha256:abc...",   # hash of output for integrity check
    "model_used": "deepseek-v4-flash",# which model was used
    "retry_count": 0,                 # how many LLM retries
    "tokens_used": {
        "input": 1500,
        "output": 800,
    }
}
```

### 6.3 Resume from Last Successful Node

```python
async def resume_workflow(workflow_id: str) -> WorkflowResult:
    """Resume workflow from last successful node"""
    workflow = await db.fetch_one(
        "SELECT * FROM workflows WHERE id = $1", workflow_id
    )

    if not workflow:
        raise WorkflowNotFoundError(workflow_id)

    # Find last successful node
    node_history = workflow["node_history"]
    last_successful = None
    for entry in reversed(node_history):
        if entry["state"] == "COMPLETED":
            last_successful = entry
            break

    if last_successful is None:
        # No successful nodes → restart from beginning
        logger.info(f"Workflow {workflow_id}: no successful nodes, restarting")
        return await start_workflow_from_beginning(workflow_id)

    # Resume from next node after last successful
    next_node = get_next_node(last_successful["node"])
    logger.info(f"Workflow {workflow_id}: resuming from node {next_node}")

    # Restore workflow context from last successful node
    context = workflow["context"]

    try:
        result = await execute_workflow_node(workflow_id, next_node, context)
        await update_workflow_state(workflow_id, "RUNNING")
        return result
    except Exception as e:
        await handle_workflow_error(workflow_id, next_node, e)
        raise
```

### 6.4 Failed Node → Block/Failed State Transition

```
┌──────────┐    Node fails     ┌──────────┐
│ RUNNING  │ ─────────────────► │  FAILED  │ ← Permanent error
└──────────┘                    └──────────┘
      │                              │
      │ Node fails                   │ Manual recovery
      │ (transient)                  │ or auto-retry
      │                              │
      ▼                              ▼
┌──────────┐                    ┌──────────┐
│ BLOCKED  │ ─── retry OK ──►  │ RUNNING  │
└──────────┘                    └──────────┘
      │
      │ Retry exhausted
      │ or no recovery possible
      ▼
┌──────────┐
│  FAILED  │
└──────────┘
```

State transition rules:

| Từ → Đến | Điều kiện |
|-----------|-----------|
| RUNNING → BLOCKED | Transient error, có thể retry |
| RUNNING → FAILED | Permanent error, hoặc retry exhausted |
| BLOCKED → RUNNING | Retry thành công, hoặc manual recovery |
| BLOCKED → FAILED | Retry exhausted, hoặc permanent error |
| FAILED → RUNNING | Manual recovery (qua API endpoint) |

### 6.5 Manual Recovery API Endpoint

```python
# POST /api/v1/workflows/{workflow_id}/recover
RECOVER_REQUEST_SCHEMA = {
    "recovery_action": "retry_node | skip_node | restart_workflow | change_model",
    "target_node": "optional — node to retry/skip",
    "new_model": "optional — model to switch to",
    "notes": "optional — reason for manual recovery",
}

RECOVER_RESPONSE_SCHEMA = {
    "workflow_id": "uuid",
    "previous_state": "FAILED/BLOCKED",
    "current_state": "RUNNING",
    "recovery_action": "retry_node",
    "resumed_from_node": "execute",
    "timestamp": "2026-05-14T10:30:00Z",
}
```

```python
@router.post("/workflows/{workflow_id}/recover")
async def recover_workflow(
    workflow_id: str,
    request: RecoverRequest,
    user_id: str = Depends(get_current_user),
) -> RecoverResponse:
    """Manual recovery endpoint for blocked/failed workflows"""

    workflow = await get_workflow(workflow_id)

    # Authorization check
    if workflow.user_id != user_id:
        raise HTTPException(403, "Not authorized to recover this workflow")

    # Only BLOCKED or FAILED workflows can be recovered
    if workflow.state not in ("BLOCKED", "FAILED"):
        raise HTTPException(400, f"Cannot recover workflow in state {workflow.state}")

    # Log recovery action
    logger.info(
        "Manual workflow recovery",
        extra={
            "workflow_id": workflow_id,
            "previous_state": workflow.state,
            "recovery_action": request.recovery_action,
            "user_id": user_id,
        }
    )

    # Execute recovery based on action type
    if request.recovery_action == "retry_node":
        result = await retry_workflow_node(workflow_id, request.target_node)
    elif request.recovery_action == "skip_node":
        result = await skip_workflow_node(workflow_id, request.target_node)
    elif request.recovery_action == "restart_workflow":
        result = await restart_workflow(workflow_id)
    elif request.recovery_action == "change_model":
        result = await retry_with_different_model(
            workflow_id, request.target_node, request.new_model
        )
    else:
        raise HTTPException(400, f"Unknown recovery action: {request.recovery_action}")

    return result
```

---

## 7. Fallback Model Chain

### 7.1 Fallback Chain Definition

Khi primary model không available (circuit breaker OPEN hoặc hết retries), hệ thống tự động chuyển sang fallback model theo chain được định nghĩa trước:

```
deepseek-v4-flash ──► deepseek-v4-pro ──► qwen-3.6-plus ──► ESCALATE TO HUMAN
                                                               │
qwen-3.5-plus ──────────────────────► qwen-3.6-plus ──► ESCALATE TO HUMAN
                                                               │
qwen-3.6-plus ───────────────────────────────────────────────► ESCALATE TO HUMAN
```

### 7.2 Fallback Configuration

```python
FALLBACK_CHAIN = {
    "deepseek-v4-flash": {
        "fallback": "deepseek-v4-pro",
        "escalation": "human",
    },
    "deepseek-v4-pro": {
        "fallback": "qwen-3.6-plus",
        "escalation": "human",
    },
    "qwen-3.5-plus": {
        "fallback": "qwen-3.6-plus",
        "escalation": "human",
    },
    "qwen-3.6-plus": {
        "fallback": None,
        "escalation": "human",
    },
}
```

### 7.3 Fallback Selection Logic

```python
async def call_with_fallback(model: str, prompt: str, config: dict) -> LLMResponse:
    """Call LLM with automatic fallback chain"""

    models_to_try = [model]
    current_model = model

    # Build fallback chain
    while FALLBACK_CHAIN.get(current_model, {}).get("fallback"):
        fallback_model = FALLBACK_CHAIN[current_model]["fallback"]
        models_to_try.append(fallback_model)
        current_model = fallback_model

    # Try each model in the chain
    last_error = None
    for try_model in models_to_try:
        circuit_breaker = get_circuit_breaker(try_model)

        if circuit_breaker.state == "OPEN":
            logger.warning(f"Skipping {try_model}: circuit breaker OPEN")
            continue

        try:
            response = await call_llm_with_retry(try_model, prompt, config)
            if try_model != model:
                logger.info(
                    f"Successfully used fallback model {try_model} "
                    f"instead of {model}"
                )
            return response

        except (RetryableError, NonRetryableError) as e:
            last_error = e
            logger.warning(f"Model {try_model} failed: {e.error_type}")
            continue

    # All models in chain exhausted → escalate to human
    logger.error(
        f"All models exhausted in fallback chain for {model}. "
        f"Last error: {last_error}"
    )
    await escalate_to_human(model, prompt, last_error)
    raise AllModelsExhaustedError(model, last_error)
```

### 7.4 Escalation to Human

Khi tất cả fallback models đều thất bại:

```python
ESCALATION_LEVELS = {
    "level_1": {
        "trigger": "Single model circuit breaker OPEN",
        "action": "Log warning, continue with fallback model",
        "channel": "monitoring_dashboard",
    },
    "level_2": {
        "trigger": "Multiple model circuit breakers OPEN",
        "action": "Send Slack alert to on-call engineer",
        "channel": "slack #ops-alerts",
    },
    "level_3": {
        "trigger": "All fallback models exhausted",
        "action": "Page on-call engineer, create incident ticket",
        "channel": "pagerduty + slack #incidents",
    },
}
```

---

## 8. Error Categories and Responses

### 8.1 Error Category Matrix

| Error Category | Example | Response | Logging Level |
|---------------|---------|----------|---------------|
| **LLM Timeout** | Model không respond trong 90s | Retry → circuit breaker → fallback model | `WARNING` |
| **LLM Rate Limit** | 429 Too Many Requests | Exponential backoff retry → fallback model | `WARNING` |
| **LLM Server Error** | 500 Internal Server Error | Retry → circuit breaker → fallback model | `ERROR` |
| **LLM Auth Failed** | 401 Invalid API Key | Fail immediately, no retry | `CRITICAL` |
| **LLM Context Exceeded** | Prompt quá token limit | Truncate prompt or fail gracefully | `WARNING` |
| **LLM Invalid Request** | 400 Bad Request | Fail immediately, log full request | `ERROR` |
| **Workflow Timeout** | Execute node exceed 10 min | Transition → BLOCKED, notify user | `ERROR` |
| **Workflow Invalid State** | Transition không hợp lệ | Log error, keep current state | `ERROR` |
| **DB Connection Lost** | PostgreSQL unreachable | Retry with backoff, queue operations | `CRITICAL` |
| **DB Query Error** | Constraint violation | Log detailed error, return 500 | `ERROR` |
| **Agent Validation Fail** | Output không match schema | Retry node (max 2), then BLOCKED | `WARNING` |
| **Agent Hallucination** | Code không compile được | Retry with corrected prompt | `WARNING` |
| **Agent Logic Error** | Sai business logic | Manual review, BLOCKED state | `WARNING` |
| **Rate Limit Exceeded** | User vượt RPM limit | Return 429 với Retry-After header | `INFO` |
| **Mentor Quota Exceeded** | User vượt 10 calls/day | Return 429, suggest upgrade tier | `INFO` |
| **Network Error** | DNS failure, connection refused | Retry với backoff | `WARNING` |
| **Config Error** | Missing env variable | Fail fast, no retry, alert on-call | `CRITICAL` |
| **Memory Error** | OOM during large context | Reduce context, retry with smaller prompt | `CRITICAL` |

### 8.2 Transient vs Permanent Errors

```
┌──────────────────────────────────────────────────────┐
│                   Error Classification                 │
├───────────────────────────────────────────────────────┤
│                                                       │
│  TRANSIENT (Tạm thời)                                │
│  ├── Timeout                                          │
│  ├── Rate limit (429)                                 │
│  ├── Server error (500/502/503)                       │
│  ├── Network errors                                   │
│  ├── DB connection issues                             │
│  └── Agent validation failures                        │
│                                                       │
│  → Xử lý: Retry → Backoff → Circuit Breaker → Fallback│
│                                                       │
│  PERMANENT (Vĩnh viễn)                                │
│  ├── Auth failed (401/403)                            │
│  ├── Invalid request (400)                            │
│  ├── Context length exceeded                          │
│  ├── Config errors                                    │
│  └── Schema violations (repeated)                     │
│                                                       │
│  → Xử lý: Log → Fail → Notify → Escalate to human    │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 8.3 Error Response Format

Mọi error response tuân theo format chuẩn:

```json
{
    "error": {
        "type": "LLM_TIMEOUT",
        "category": "TRANSIENT",
        "code": "E_LLM_TIMEOUT_001",
        "message": "DeepSeek V4 Flash timed out after 30s",
        "detail": {
            "model": "deepseek-v4-flash",
            "timeout_seconds": 30,
            "attempt": 3,
            "fallback_used": "deepseek-v4-pro"
        },
        "retry_eligible": true,
        "suggested_action": "The request will be retried with a fallback model.",
        "trace_id": "trace-abc-123",
        "timestamp": "2026-05-14T10:30:00.000Z"
    }
}
```

### 8.4 Error Code Convention

```
E_{COMPONENT}_{ERROR_TYPE}_{NUMBER}

Components:
  LLM      - LLM provider errors
  WF       - Workflow errors
  AGENT    - Agent errors
  DB       - Database errors
  API      - API/Rate limit errors
  SYS      - System errors

Error Types:
  TIMEOUT  - Timeout errors
  AUTH     - Authentication/authorization errors
  RATE     - Rate limit errors
  CONFIG   - Configuration errors
  VALID    - Validation errors
  CONN     - Connection errors
  STATE    - State transition errors

Examples:
  E_LLM_TIMEOUT_001    - LLM call timeout
  E_WF_STATE_001       - Invalid workflow state transition
  E_AGENT_VALID_001    - Agent output validation failed
  E_API_RATE_001       - User rate limit exceeded
  E_DB_CONN_001        - Database connection lost
```

---

## 9. Monitoring & Alerting

### 9.1 Error Rate Thresholds

```python
ERROR_RATE_THRESHOLDS = {
    "global_error_rate": {
        "warning": 0.05,    # 5% error rate → WARNING
        "critical": 0.10,   # 10% error rate → CRITICAL
        "window": "5m",     # rolling 5-minute window
    },
    "llm_error_rate": {
        "warning": 0.10,    # 10% LLM error rate
        "critical": 0.25,   # 25% LLM error rate
        "window": "5m",
    },
    "workflow_failure_rate": {
        "warning": 0.05,    # 5% workflow failure rate
        "critical": 0.15,   # 15% workflow failure rate
        "window": "15m",
    },
}
```

### 9.2 Circuit Breaker State Monitoring

```python
CIRCUIT_BREAKER_ALERTS = {
    "circuit_opened": {
        "condition": "Any circuit breaker transitions to OPEN",
        "severity": "WARNING",
        "channel": "slack #ops-alerts",
        "message": "Circuit breaker OPEN for {model}. Fallback to {fallback_model}.",
        "auto_resolve": True,  # tự resolve khi circuit đóng lại
    },
    "circuit_half_open": {
        "condition": "Circuit breaker enters HALF_OPEN state",
        "severity": "INFO",
        "channel": "monitoring_dashboard",
        "message": "Circuit breaker HALF_OPEN for {model}. Testing recovery...",
    },
    "circuit_stuck_open": {
        "condition": "Circuit breaker remains OPEN for > 10 minutes",
        "severity": "CRITICAL",
        "channel": "pagerduty + slack #incidents",
        "message": "Circuit breaker stuck OPEN for {model} over 10 min. Manual intervention needed.",
        "auto_resolve": False,
    },
    "multiple_circuits_open": {
        "condition": "2+ circuit breakers OPEN simultaneously",
        "severity": "CRITICAL",
        "channel": "pagerduty + slack #incidents",
        "message": "Multiple circuit breakers OPEN. System degradation likely.",
    },
}
```

### 9.3 LLM Call Success Rate Monitoring

```python
LLM_MONITORING_METRICS = {
    "success_rate": {
        "description": "Percentage of successful LLM calls",
        "calculation": "successful_calls / total_calls * 100",
        "dimensions": ["model", "agent_type", "user_tier"],
        "alert_threshold": {
            "warning": 90,    # < 90% success rate
            "critical": 75,   # < 75% success rate
        },
    },
    "latency_p50": {
        "description": "50th percentile LLM response time",
        "dimensions": ["model"],
        "alert_threshold": {
            "warning": "2x baseline",  # 2x normal latency
            "critical": "5x baseline", # 5x normal latency
        },
    },
    "latency_p99": {
        "description": "99th percentile LLM response time",
        "dimensions": ["model"],
        "alert_threshold": {
            "warning": "timeout * 0.8",  # 80% of timeout
            "critical": "timeout * 0.95", # 95% of timeout
        },
    },
    "token_usage": {
        "description": "Token consumption rate",
        "dimensions": ["model", "user_id", "agent_type"],
        "aggregation": "sum per hour",
        "budget_alert": True,
    },
    "fallback_rate": {
        "description": "Percentage of calls using fallback model",
        "calculation": "fallback_calls / total_calls * 100",
        "alert_threshold": {
            "warning": 10,    # > 10% using fallback
            "critical": 30,   # > 30% using fallback
        },
    },
}
```

### 9.4 Alert Escalation Rules

```
┌─────────────────────────────────────────────────────────┐
│                Alert Escalation Matrix                    │
├───────────────┬─────────────────────────────────────────┤
│   Severity    │         Escalation Path                  │
├───────────────┼─────────────────────────────────────────┤
│               │                                         │
│  INFO         │  Dashboard only                          │
│               │  → Monitoring dashboard badge            │
│               │                                         │
│  WARNING      │  Dashboard + Slack                       │
│               │  → #ops-alerts channel                   │
│               │  → Auto-resolve when recovered           │
│               │                                         │
│  CRITICAL     │  Dashboard + Slack + PagerDuty           │
│               │  → #incidents channel                    │
│               │  → Page on-call engineer                 │
│               │  → Create incident ticket                │
│               │                                         │
│  EMERGENCY    │  All channels + Management               │
│               │  → Page on-call + backup                 │
│               │  → #incidents + #exec-alerts            │
│               │  → War room if > 15min                   │
│               │                                         │
└───────────────┴─────────────────────────────────────────┘
```

### 9.5 Alert Escalation Specific Rules

```python
ESCALATION_RULES = {
    "single_model_down": {
        "trigger": "One model circuit OPEN for > 5 minutes",
        "severity": "WARNING",
        "auto_action": "Traffic rerouted to fallback model",
        "human_action": "Investigate provider status",
        "sla": "Acknowledge in 15 minutes",
    },
    "multiple_models_down": {
        "trigger": "2+ models circuit OPEN simultaneously",
        "severity": "CRITICAL",
        "auto_action": "All traffic to remaining healthy models",
        "human_action": "Check provider status, consider启用 manual circuit close",
        "sla": "Acknowledge in 5 minutes",
    },
    "all_models_down": {
        "trigger": "All model circuit breakers OPEN",
        "severity": "EMERGENCY",
        "auto_action": "Maintainence mode, return 503 to all requests",
        "human_action": "Contact provider, activate DR plan",
        "sla": "Acknowledge in 1 minute",
    },
    "error_rate_spike": {
        "trigger": "Global error rate > 10% for 5 minutes",
        "severity": "CRITICAL",
        "auto_action": "Enable verbose logging",
        "human_action": "Identify root cause, consider circuit breaker reset",
        "sla": "Acknowledge in 10 minutes",
    },
    "workflow_failure_spike": {
        "trigger": "Workflow failure rate > 15% for 15 minutes",
        "severity": "CRITICAL",
        "auto_action": "Pause new workflow submissions",
        "human_action": "Review failed workflows, identify pattern",
        "sla": "Acknowledge in 10 minutes",
    },
    "mentor_quota_anomaly": {
        "trigger": "Mentor quota usage > 3x average for user tier",
        "severity": "WARNING",
        "auto_action": "Flag for review",
        "human_action": "Investigate potential abuse or misuse",
        "sla": "Review within 1 hour",
    },
}
```

### 9.6 Monitoring Dashboard Metrics

```
┌────────────────────────────────────────────────────────────┐
│                  Monitoring Dashboard                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─ Circuit Breaker Status ─────────────────────────────┐ │
│  │ deepseek-v4-flash: [CLOSED] ✅  failures: 0/5         │ │
│  │ deepseek-v4-pro:   [CLOSED] ✅  failures: 1/5         │ │
│  │ qwen-3.5-plus:     [CLOSED] ✅  failures: 0/5         │ │
│  │ qwen-3.6-plus:     [OPEN]   🔴  failures: 5/5  45s   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌─ LLM Success Rate (5m) ──────────────────────────────┐ │
│  │ deepseek-v4-flash: ████████████████████░░ 96.2%       │ │
│  │ deepseek-v4-pro:   ██████████████████░░░░ 89.1%       │ │
│  │ qwen-3.5-plus:     ████████████████████░░ 98.5%       │ │
│  │ qwen-3.6-plus:     ██████░░░░░░░░░░░░░░░░ 34.2% ⚠️    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌─ Active Workflows ───────────────────────────────────┐ │
│  │ RUNNING: 23  BLOCKED: 3  FAILED: 1  COMPLETED: 156    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌─ Recent Alerts ──────────────────────────────────────┐ │
│  │ ⚠️  qwen-3.6-plus circuit OPEN (escalated 2m ago)    │ │
│  │ ℹ️  deepseek-v4-pro circuit recovered (10m ago)       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 9.7 Log Standards (LAW-006 Compliance)

Mọi error log phải bao gồm đầy đủ context theo LAW-006:

```python
import structlog

logger = structlog.get_logger()

# Mọi error log phải có các field bắt buộc
logger.error(
    "llm_call_failed",
    model="deepseek-v4-flash",
    agent_type="coder",
    workflow_id="wf-123",
    node_type="execute",
    error_type="timeout",
    error_category="TRANSIENT",
    attempt=3,
    max_retries=3,
    duration_ms=30000,
    input_token_count=1500,
    circuit_breaker_state="CLOSED",
    fallback_triggered=True,
    fallback_model="deepseek-v4-pro",
    trace_id="trace-abc-123",
    user_id="user-456",
    project_id="proj-789",
    timestamp="2026-05-14T10:30:00.000Z",
)
```

Required log fields cho mọi error:

| Field | Mô tả | Required |
|-------|--------|----------|
| `model` | LLM model đang sử dụng | Yes (cho LLM errors) |
| `agent_type` | Loại agent (coder, reviewer, mentor) | Yes |
| `workflow_id` | Workflow ID | Yes |
| `node_type` | Node đang execute (execute, verify, review) | Yes |
| `error_type` | Loại error cụ thể | Yes |
| `error_category` | TRANSIENT hoặc PERMANENT | Yes |
| `attempt` | Số lần retry hiện tại | Yes |
| `max_retries` | Max retries configured | Yes |
| `circuit_breaker_state` | Trạng thái circuit breaker | Yes |
| `trace_id` | Distributed trace ID | Yes |
| `user_id` | User ID | Yes |
| `timestamp` | ISO 8601 timestamp | Yes |

---

## 12. Concurrency & Locking Strategy (v4.1 — Risk #1 Fix)

### 12.1 Optimistic Locking

Mọi state transition sử dụng **optimistic locking** với `version` column trên tasks table:

```python
# shared/models/task.py
version = Column(Integer, nullable=False, default=0)

# services/tasks.py — transition_task_state
async def transition_task_state(db, task_id, request, expected_version=None):
    task = await db.execute(
        select(Task).where(Task.id == task_id).with_for_update()
    )
    if expected_version and task.version != expected_version:
        raise OptimisticLockError(
            f"Task {task_id} was modified by another process"
        )
    task.status = request.target_status
    task.version += 1  # Increment on every update
```

### 12.2 Retry on Conflict

Decorator `@retry_on_conflict` tự động retry khi phát hiện concurrent update:

```python
from shared.concurrency import retry_on_conflict, OptimisticLockError

@retry_on_conflict(max_retries=3, base_delay=0.1, max_delay=2.0)
async def transition_task_state(db, task_id, request, expected_version=None):
    ...
```

Retry với exponential backoff: 0.1s → 0.2s → 0.4s → fail

### 12.3 Stuck Task Detection

Background job chạy định kỳ (mỗi 5 phút) để phát hiện và auto-escalate stuck tasks:

| Timeout | Action |
|---|---|
| 30 phút | Detect stuck task, log warning |
| 60 phút | Auto-escalate to ESCALATED state |
| 120 phút (BLOCKED) | Auto-escalate BLOCKED → ESCALATED |

```python
from services.orchestrator.services.stuck_task_detector import run_stuck_task_detection

# Run every 5 minutes
result = await run_stuck_task_detection(db)
# result: {
#   "stuck_tasks_detected": 3,
#   "blocked_tasks_auto_escalated": 1,
#   "stuck_tasks_auto_escalated": 2,
# }
```

### 12.4 Zombie Task Prevention

- `SELECT FOR UPDATE` locks task row during transition
- Version increment ensures concurrent updates are detected
- Background detector catches any tasks that slip through
- Admin API for manual force transition (Phase 2)

---

## 13. Context Window Management (v4.1 — Risk #2 Fix)

### 13.1 Priority-Based Truncation

Context builder với priority levels (0-100) đảm bảo thông tin quan trọng nhất luôn được giữ:

| Priority | Section | Always Included? |
|---|---|---|
| 100 | Task description | Yes |
| 90 | Output format | Yes |
| 80 | System prompt / agent role | Yes |
| 70 | Self-awareness prompt | Yes |
| 60 | Validation gate results | Yes |
| 50 | Relevant memory | Truncate if needed |
| 40 | Module specs | Truncate if needed |
| 30 | Architectural laws | Truncate if needed |
| 20 | Full codebase | Truncate first |
| 10 | Historical logs | Truncate first |

```python
from services.orchestrator.services.context_builder import ContextBuilder

builder = ContextBuilder(max_tokens=128000, safety_margin=4096)
builder.add_section("Task Description", task_desc, priority=100)
builder.add_section("Architectural Laws", laws, priority=30)
builder.add_section("Relevant Memory", memory, priority=50)
context = builder.build()
```

### 13.2 "Lost in the Middle" Mitigation

Research cho thấy LLMs chú ý nhất đến:
- **Đầu context** (~20% đầu)
- **Cuối context** (~20% cuối)
- **Ít chú ý nhất**: giữa context (~60%)

ContextBuilder tự động reorder sections:
- Priority >= 80: **BEGINNING**
- Priority 40-79: **MIDDLE**
- Priority < 40: **END**

### 13.3 Context Overflow Protocol

Khi context vẫn vượt limit sau truncation:
1. Log overflow event
2. Escalate task — yêu cầu user chia nhỏ task
3. Force switch sang model có context limit lớn hơn (Qwen 3.6 Plus: 1M tokens)
4. Reduce context — chỉ giữ task description + essential info

---

## 14. BLOCKED State Resolution Protocol (v4.1 — Risk #3 Fix)

### 14.1 BLOCKED Timeout Mechanism

BLOCKED state không còn là "hố đen" — có timeout và auto-escalation:

| Thời gian | Action |
|---|---|
| 0 phút | Task enters BLOCKED, notification sent to user |
| 60 phút | Warning notification (HIGH priority) |
| 120 phút | Auto-escalate to ESCALATED, Mentor review |

### 14.2 Human-in-the-Loop Notifications

Khi task bị BLOCKED, hệ thống tự động gửi notification:

```python
from services.orchestrator.services.notification_service import (
    create_blocked_notification,
    notification_service,
)

notification = create_blocked_notification(
    task_id=task.id,
    project_id=task.project_id,
    task_title=task.title,
    reason="Missing dependency: auth module not complete",
    missing_info=["auth module spec", "API endpoint requirements"],
)
await notification_service.send(notification)
```

Notification channels:
- **DASHBOARD**: WebSocket real-time
- **SLACK**: Team channel alert
- **EMAIL**: Critical notifications
- **WEBHOOK**: Custom integrations

### 14.3 BLOCKED → ESCALATED Transition

BLOCKED state giờ có 3 exits (was 2):
- `BLOCKED → PLANNING`: Dependency resolved
- `BLOCKED → CANCELLED`: User cancels
- `BLOCKED → ESCALATED`: **NEW** — Timeout auto-escalation (120+ minutes)

### 14.4 Notification Database

Notifications stored in `notifications` table for audit and retry:

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    project_id UUID REFERENCES projects(id),
    notification_type VARCHAR(50),
    title VARCHAR(500),
    message TEXT,
    priority VARCHAR(20),
    channels JSONB,
    metadata JSONB,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```