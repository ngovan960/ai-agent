# LLM Integration Design Document

## AI SDLC System - Tài liệu Thiết kế Tích hợp LLM

---

## 1. Overview

FastAPI backend đóng vai trò **brain** — trung tâm điều phối tất cả các LLM calls trong hệ thống AI SDLC. Mọi request từ agents đều đi qua FastAPI LLM Gateway, được route đến model phù hợp qua 2 paths, và xử lý fallback tự động khi cần thiết.

### 1.1 LLM Gateway Architecture

FastAPI LLM Gateway có **2 paths** để gọi LLM:

```
Path 1: LiteLLM trực tiếp (cho agents không cần tools)
  FastAPI → LLM Gateway → LiteLLM → Provider API (DeepSeek/Qwen)
  Agents: Gatekeeper, Orchestrator, Mentor, Monitoring

Path 2: OpenCode integration (cho agents cần tools)
  FastAPI → LLM Gateway → OpenCode → {LLM call + Tool execution}
  Agents: Specialist, Auditor, DevOps
```

### 1.2 Danh sách Models

| Model | Provider | Context Window | Speed | Cost | Đặc điểm |
|-------|----------|---------------|-------|------|----------|
| DeepSeek V4 Flash | DeepSeek | 64K | Rất nhanh | Thấp | Phù hợp cho task đơn giản, tốc độ ưu tiên |
| DeepSeek V4 Pro | DeepSeek | 128K | Trung bình | Cao | Reasoning sâu, phù hợp cho task phức tạp |
| Qwen 3.5 Plus | Alibaba | 128K | Trung bình | Trung bình | Cân bằng giữa chất lượng và chi phí |
| Qwen 3.6 Plus | Alibaba | 256K | Chậm | Cao | Chất lượng cao nhất, phù hợp cho architecture & planning |

### 1.3 Model Routing Logic

Model routing dựa trên **agent type** và **task complexity**:

```
Agent              | Primary Model          | LLM Path      | Fallback Chain
━━━━━━━━━━━━━━━━━━|━━━━━━━━━━━━━━━━━━━━━━━━|━━━━━━━━━━━━━━|━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gatekeeper         | DeepSeek V4 Flash      | LiteLLM       | DeepSeek V4 Pro → Qwen 3.5 Plus
Orchestrator       | Qwen 3.6 Plus          | LiteLLM       | DeepSeek V4 Pro → Qwen 3.5 Plus
Specialist         | DeepSeek V4 Pro        | OpenCode      | Qwen 3.6 Plus → Qwen 3.5 Plus
Auditor            | Qwen 3.5 Plus          | LiteLLM       | Qwen 3.6 Plus → DeepSeek V4 Pro
Mentor             | Qwen 3.6 Plus          | LiteLLM       | DeepSeek V4 Pro → Qwen 3.5 Plus
DevOps             | DeepSeek V4 Pro        | OpenCode      | Qwen 3.6 Plus → Qwen 3.5 Plus
Monitoring         | DeepSeek V4 Flash      | LiteLLM       | DeepSeek V4 Pro → Qwen 3.5 Plus
```

**Quy tắc routing:**
- **LiteLLM path**: Dùng cho agents chỉ cần LLM để phân tích, phân loại, planning — không cần truy cập filesystem
- **OpenCode path**: Dùng cho agents cần tools (bash, edit, write, read, glob, grep) để thao tác với code

### 1.4 Fallback Chain cho Resilience

Khi một model call thất bại, FastAPI tự động fallback theo chain đã định nghĩa:

```
Call Flow với Fallback:

1. Gọi Primary Model (via LiteLLM hoặc OpenCode)
   ├─ Success → Return response
   └─ Failure (timeout/rate-limit/error)
       ├─ Retry với exponential backoff (tối đa 3 lần)
       │   ├─ Success → Return response
       │   └─ Still failing → Try Fallback Model 1
       │       ├─ Success → Return response
       │       └─ Still failing → Try Fallback Model 2
       │           ├─ Success → Return response
       │           └─ Still failing → Return error, log incident, alert team
```

**Exponential Backoff:**
- Retry 1: wait 1s
- Retry 2: wait 2s
- Retry 3: wait 4s
- Sau 3 retries, chuyển sang fallback model

---

## 2. LLM Call Architecture

### 2.1 Kiến trúc Tổng thể

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Agent   │────▶│   FastAPI     │────▶│  LLM Gateway    │────▶│ Circuit       │
│ Request  │     │  Brain        │     │  Service         │     │ Breaker       │
└──────────┘     └──────────────┘     └────────┬─────────┘     └──────┬───────┘
                                             │                         │
                                    ┌────────┴────────┐               ▼
                                    │  Path Selection │        ┌──────────────┐
                                    │                 │        │ Provider API  │
                                    │ LiteLLM  OpenCode│        │ (DeepSeek /   │
                                    │ (simple) (tools) │        │  Qwen)        │
                                    └─────────────────┘        └──────────────┘
                                             │
                                      ┌──────┴────────┐
                                      │  Logging &     │
                                      │  Cost Tracking │
                                      └────────────────┘
```

### 2.2 LLM Gateway Service

LLM Gateway là **single entry point** cho tất cả LLM calls trong FastAPI, đảm bảo:
- **Centralized logging**: Mọi call đều được log vào `llm_call_logs` và `cost_tracking`
- **Rate limiting**: Quản lý concurrent requests per provider
- **Circuit breaker**: Bảo vệ hệ thống khỏi cascading failures
- **Path selection**: Chọn LiteLLM hoặc OpenCode dựa trên agent type
- **Load balancing**: Phân bổ requests giữa providers khi cần

```python
# FastAPI LLM Gateway - Pseudocode
class LLMGateway:
    def call(self, request: LLMRequest) -> LLMResponse:
        # 1. Validate request
        self.validate_request(request)

        # 2. Check rate limits
        self.rate_limiter.check(request.model, request.tenant_id)

        # 3. Select path based on agent type
        if request.agent_needs_tools:
            path = self.opencode_path
        else:
            path = self.litellm_path

        # 4. Build circuit breaker key
        cb_key = f"{request.provider}:{request.model}"

        # 5. Execute call through circuit breaker
        response = self.circuit_breakers[cb_key].execute(
            lambda: path.call(request)
        )

        # 6. Log call details
        self.log_call(request, response)

        # 7. Track costs
        self.track_cost(request, response)

        return response
```

### 2.3 Circuit Breaker Pattern

Mỗi provider-model combination được bảo vệ bởi một Circuit Breaker riêng:

```
Circuit Breaker States:

CLOSED (Bình thường)
  └─ Requests đi qua bình thường
  └─ Nếu có >=5 consecutive failures trong 60s → chuyển sang OPEN

OPEN (Bật cắt)
  └─ Tất cả requests bị từ chối ngay lập tức (fast-fail)
  └─ Triggers fallback model
  └─ Sau 30s → chuyển sang HALF-OPEN

HALF-OPEN (Thử lại)
  └─ Cho phép 1 request đi qua (probe request)
  └─ Nếu thành công → chuyển sang CLOSED
  └─ Nếu thất bại → chuyển sang OPEN, reset timer
```

### 2.4 Logging Schema

**llm_call_logs table:**

```sql
CREATE TABLE llm_call_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID REFERENCES tasks(id),
    agent_type      VARCHAR(50) NOT NULL,        -- 'gatekeeper', 'specialist', etc.
    model          VARCHAR(50) NOT NULL,          -- 'deepseek-v4-flash', etc.
    provider        VARCHAR(30) NOT NULL,          -- 'deepseek', 'qwen'
    llm_path        VARCHAR(20) NOT NULL,          -- 'litellm' or 'opencode'
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    cost_usd        DECIMAL(10, 6) NOT NULL,
    latency_ms      INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL,          -- 'success', 'error', 'timeout', 'fallback'
    error_message   TEXT,
    fallback_used   BOOLEAN DEFAULT FALSE,
    fallback_model  VARCHAR(50),
    prompt_hash     VARCHAR(64),                   -- SHA-256 hash of prompt template
    created_at      TIMESTAMP DEFAULT NOW(),

    INDEX idx_llm_call_logs_task (task_id),
    INDEX idx_llm_call_logs_model (model),
    INDEX idx_llm_call_logs_created (created_at)
);
```

**cost_tracking table (aggregate):**

```sql
CREATE TABLE cost_tracking (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    task_id         UUID REFERENCES tasks(id),
    date            DATE NOT NULL,
    model           VARCHAR(50) NOT NULL,
    total_calls     INTEGER DEFAULT 0,
    total_input_tokens  INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost_usd  DECIMAL(10, 4) DEFAULT 0,
    avg_latency_ms  INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    fallback_count  INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE (project_id, task_id, date, model)
);
```

---

## 3. Agent-Model Mapping

### 3.1 Bảng Mapping chính

| Agent | Primary Model | LLM Path | Fallback Model | Timeout (s) | Use Case |
|-------|--------------|----------|----------------|-------------|----------|
| Gatekeeper | DeepSeek V4 Flash | LiteLLM | DeepSeek V4 Pro → Qwen 3.5 Plus | 30 | Phân loại yêu cầu, routing |
| Orchestrator | Qwen 3.6 Plus | LiteLLM | DeepSeek V4 Pro → Qwen 3.5 Plus | 120 | Chia task, lập kế hoạch |
| Specialist | DeepSeek V4 Pro | OpenCode | Qwen 3.6 Plus → Qwen 3.5 Plus | 60 | Viết code, implement |
| Auditor | Qwen 3.5 Plus | LiteLLM | Qwen 3.6 Plus → DeepSeek V4 Pro | 60 | Review code, check quality |
| Mentor | Qwen 3.6 Plus | LiteLLM | DeepSeek V4 Pro → Qwen 3.5 Plus | 30 | Quyết định chiến lược |
| DevOps | DeepSeek V4 Pro | OpenCode | Qwen 3.6 Plus → Qwen 3.5 Plus | 45 | Build, deploy, CI/CD |
| Monitoring | DeepSeek V4 Flash | LiteLLM | DeepSeek V4 Pro → Qwen 3.5 Plus | 15 | Giám sát, phát hiện anomaly |

### 3.2 Context Building cho mỗi Agent Call

Mỗi agent call cần context khác nhau, được build bởi **FastAPI Context Builder**:

```
Gatekeeper Context:
├── User request (full)
├── Related memory (from pgvector)
└── Prompt template: gatekeeper.txt

Orchestrator Context:
├── Classified task (from Gatekeeper)
├── Project state (modules, tasks, dependencies)
├── Related memory (from pgvector)
├── Architectural laws (subset)
└── Prompt template: orchestrator.txt

Specialist Context:
├── Task description (full)
├── Relevant code files (via embedding search)
├── Architecture decisions
├── Code style guide (from memory)
├── Architectural laws (subset: coding standards)
└── Prompt template: coder.txt

Auditor Context:
├── Task description (summary)
├── Code to review
├── Architecture decisions
├── Security checklist
├── Quality standards (from memory)
├── Architectural laws (subset: review criteria)
└── Prompt template: reviewer.txt
```

### 3.3 Prompt Template System

Templates được lưu tại `/agents/prompts/*.txt`, mỗi template chứa:
- **System prompt**: Role definition, behavioral guidelines
- **Variable placeholders**: Sẽ được thay thế bằng context thực tế
- **Output format specification**: JSON schema hoặc structured format

---

## 4. Context Window Management

### 4.1 Context Size Limits per Model

Mỗi model có **effective context limit** riêng (không dùng toàn bộ context window, giữ lại margin cho output):

| Model | Full Context Window | Effective Input Limit | Reserved for Output |
|-------|--------------------|-----------------------|---------------------|
| DeepSeek V4 Flash | 64K tokens | 4096 tokens | 1024 tokens |
| DeepSeek V4 Pro | 128K tokens | 8192 tokens | 2048 tokens |
| Qwen 3.5 Plus | 128K tokens | 8192 tokens | 2048 tokens |
| Qwen 3.6 Plus | 256K tokens | 16384 tokens | 4096 tokens |

> **Lưu ý**: Effective input limits ở trên là **default values** cho AI SDLC system, được giới hạn thấp hơn context window thực tế để:
> 1. Kiểm soát chi phí (nhiều tokens = chi phí cao hơn)
> 2. Đảm bảo output quality (model hoạt động tốt hơn với context vừa phải)
> 3. Giữ reserve cho output generation

### 4.2 Context Builder Pipeline

```
Context Builder Pipeline (FastAPI):

┌─────────────────────┐
│ 1. Load Task Spec    │  ← Always loaded, highest priority
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. Load Related     │  ← Embedding search: find related modules,
│    Modules          │     specs, and past decisions from memory
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 3. Load Relevant    │  ← From vector memory: past context,
│    Memory           │     lessons learned, decisions relevant to task
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 4. Load Arch        │  ← Architectural laws, filtered by relevance
│    Laws             │     to current task type
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5. Apply Truncation │  ← If total exceeds limit, truncate
│    Strategy         │     by priority (see 4.3)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 6. Render Prompt    │  ← Substitute variables into template
└─────────────────────┘
```

### 4.3 Truncation Strategy

Khi tổng context vượt quá effective input limit, thực hiện truncation theo **priority order**:

```
Priority Order (Cao → Thấp):

1. Task Description       — Priority 100 — KHÔNG BAO GIỜ cắt, nếu quá lớn thì summarize
2. Output Format Spec     — Priority 90  — KHÔNG BAO GIỜ cắt
3. System Prompt          — Priority 80  — KHÔNG cắt
4. Relevant Memory        — Priority 50  — Cắt items cũ nhất trước, giữ recent
5. Related Modules        — Priority 40  — Cắt modules ít relevant trước
6. Architectural Laws     — Priority 30  — Cắt laws ít relevant trước
```

---

## 5. Token Tracking & Cost Management

### 5.1 Chi tiết Logging per Call

Mỗi LLM call log các thông tin sau vào `llm_call_logs`:

```python
@dataclass
class LLMCallLog:
    task_id: UUID
    agent_type: str            # 'gatekeeper', 'specialist', etc.
    model: str                 # 'deepseek-v4-flash', 'qwen-3.6-plus', etc.
    provider: str              # 'deepseek', 'qwen'
    llm_path: str              # 'litellm' or 'opencode'
    input_tokens: int          # Số tokens đầu vào
    output_tokens: int         # Số tokens đầu ra
    cost_usd: float            # Chi phí USD (calculated từ pricing table)
    latency_ms: int            # Thời gian response (ms)
    status: str                # 'success', 'error', 'timeout', 'fallback'
    error_message: str | None  # Chi tiết lỗi nếu có
    fallback_used: bool        # Có dùng fallback model không
    fallback_model: str | None # Model fallback đã dùng
    prompt_hash: str            # SHA-256 hash của prompt template
    created_at: datetime
```

### 5.2 Pricing Table (per 1M tokens)

| Model | Input (USD/1M) | Output (USD/1M) | Notes |
|-------|----------------|-----------------|-------|
| DeepSeek V4 Flash | $0.10 | $0.30 | Economical, fast |
| DeepSeek V4 Pro | $0.50 | $1.50 | High quality, reasoning |
| Qwen 3.5 Plus | $0.30 | $0.90 | Balanced |
| Qwen 3.6 Plus | $0.80 | $2.40 | Premium quality |

### 5.3 Cost Alerts & Limits

**Daily Cost Alerts:**

```
Alert Levels:

WARNING  → Khi daily cost vượt $5/project
CRITICAL → Khi daily cost vượt $20/project
BLOCKED  → Khi daily cost vượt configured limit (default: $50/project)
           └─ Tất cả LLM calls cho project đó bị tạm dừng
           └─ Required: manual approval để resume
```

---

## 6. Prompt Template System

### 6.1 Template Storage & Structure

Templates được lưu tại:

```
/agents/prompts/
├── gatekeeper.txt             # Gatekeeper agent prompt
├── orchestrator.txt           # Orchestrator agent prompt
├── coder.txt                  # Specialist agent prompt
├── reviewer.txt               # Auditor agent prompt
├── mentor.txt                 # Mentor agent prompt
├── devops.txt                 # DevOps agent prompt
├── monitoring.txt             # Monitoring agent prompt
└── shared/
    ├── system_prefix.txt      # Common system prompt prefix
    ├── output_schemas.json    # JSON schemas cho output formats
    └── architectural_laws.txt # Full architectural laws text
```

### 6.2 Variable Substitution

Templates sử dụng **curly brace** notation cho variable substitution:

```
Available Variables:

{task_spec}              — Mô tả task từ user hoặc từ previous agent
{context}                — Context đã được build bởi FastAPI Context Builder
{architectural_laws}     — Relevant architectural laws (filtered)
{project_name}            — Tên dự án
{related_memory}          — Related items from vector memory
{output_schema}           — JSON schema cho expected output format
{agent_role}              — Role description của agent
{task_type}               — Loại task: 'spec', 'architecture', 'code', 'review', etc.
{module_name}              — Tên module đang xử lý (nếu có)
{previous_output}          — Output từ agent trước trong pipeline (nếu có)
```

---

## 7. LLM Call Flow (Detailed Sequence)

### 7.1 Step-by-Step Flow (FastAPI)

```
Step 1: Agent Request
━━━━━━━━━━━━━━━━━━━━
FastAPI Agent Router gửi request đến LLM Gateway:
    - agent_type: 'specialist'
    - task_id: UUID
    - task_spec: "Implement user authentication module"
    - needs_tools: true  (Specialist cần bash, edit, write)


Step 2: Context Build
━━━━━━━━━━━━━━━━━━━━━
FastAPI → Context Builder:
    a) Load task spec từ database
    b) Embedding search: tìm related modules & specs
    c) Load relevant memory từ pgvector
    d) Load architectural laws (filtered by task type)
    e) Apply truncation strategy nếu context quá lớn
    f) Return: ContextParts[] với token counts


Step 3: Prompt Render
━━━━━━━━━━━━━━━━━━━━━
FastAPI → PromptRenderer:
    a) Load template cho agent type (coder.txt)
    b) Load shared system prefix
    c) Substitute variables: {task_spec}, {context}, ...
    d) Compute prompt_hash (SHA-256)
    e) Return: rendered_prompt, prompt_hash, estimated_tokens


Step 4: Path Selection
━━━━━━━━━━━━━━━━━━━━━━
FastAPI → LLM Gateway:
    a) Check if agent needs tools
    b) If needs_tools → Path 2: OpenCode
    c) If no tools → Path 1: LiteLLM
    d) Return: selected_path, selected_model, fallback_chain


Step 5: Circuit Breaker Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FastAPI → LLM Gateway → CircuitBreaker:
    a) Check circuit state cho (provider, model)
    b) Nếu CLOSED → cho phép request
    c) Nếu OPEN → skip trực tiếp sang fallback model
    d) Nếu HALF-OPEN → cho phép 1 probe request


Step 6: API Call (với Retry & Fallback)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM Gateway → Provider API (via LiteLLM hoặc OpenCode):
    a) Record start_time
    b) Send request đến provider
    c) Nếu thành công → parse response, calculate cost
    d) Nếu thất bại:
        - Retry 1: wait 1s, retry same model
        - Retry 2: wait 2s, retry same model
        - Retry 3: wait 4s, retry same model
        - Sau 3 retries: chuyển sang next model trong fallback chain
    e) Record end_time, calculate latency_ms


Step 7: Response Parse
━━━━━━━━━━━━━━━━━━━━━
FastAPI → ResponseParser:
    a) Parse JSON response từ LLM
    b) Validate against output_schema
    c) Nếu validation fail → retry với same model (1 lần)
    d) Extract metadata: usage tokens, finish_reason
    e) Normalize response format


Step 8: Log & Track
━━━━━━━━━━━━━━━━━━━
FastAPI → Database:
    a) Insert vào llm_call_logs:
        - task_id, agent_type, model, provider, llm_path
        - input_tokens, output_tokens, cost_usd
        - latency_ms, status, error_message
        - fallback_used, fallback_model, prompt_hash
    b) Upsert vào cost_tracking:
        - Aggregate per (project_id, task_id, date, model)
    c) Check cost alerts:
        - Compare daily cost vs thresholds
        - Send alerts nếu needed


Step 9: Return to Agent Router
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FastAPI LLM Gateway → Agent Router:
    a) Return parsed response
    b) Include metadata:
        - model_used (có thể khác primary do fallback)
        - tokens_used
        - cost_usd
        - latency_ms
        - fallback_triggered (boolean)
        - llm_path_used (litellm or opencode)
```

### 7.2 Sequence Diagram

```
Agent          FastAPI       ContextBuilder   PromptRenderer   ModelRouter   LLMGateway   CircuitBreaker   ProviderAPI   DB
  │               │                │                │               │             │              │               │         │
  │──request─────▶│                │                │               │             │              │               │         │
  │               │──build_ctx────▶│                │               │             │              │               │         │
  │               │◀──context──────│                │               │             │              │               │         │
  │               │──render────────────────────────▶│               │             │              │               │         │
  │               │◀──prompt───────────────────────│               │             │              │               │         │
  │               │──select_path──────────────────────────────────▶│             │              │               │         │
  │               │◀──path────────────────────────────────────────│             │              │               │         │
  │               │──call──────────────────────────────────────────────────────▶│              │               │         │
  │               │                │                │               │             │──check───────▶│               │         │
  │               │                │                │               │             │◀──state───────│               │         │
  │               │                │                │               │             │──api_call────────────────────▶│         │
  │               │                │                │               │             │◀──response─────────────────────│         │
  │               │                │                │               │             │──log──────────────────────────────────▶│
  │               │                │                │               │             │──track_cost──────────────────────────▶│
  │◀──response────│                │                │               │             │              │               │         │
  │               │                │                │               │             │              │               │         │
```

---

## 8. Embedding Integration

### 8.1 Embedding Models Configuration

Hệ thống hỗ trợ **configurable embedding models** qua `embedding_config` table:

```sql
CREATE TABLE embedding_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name      VARCHAR(100) NOT NULL UNIQUE,
    provider        VARCHAR(50) NOT NULL,          -- 'openai', 'bge', etc.
    dimensions      INTEGER NOT NULL,               -- Vector dimensions
    max_input_tokens INTEGER NOT NULL,              -- Max input tokens
    cost_per_1k     DECIMAL(10, 6) DEFAULT 0,       -- Cost per 1K tokens
    is_active       BOOLEAN DEFAULT FALSE,          -- Only one active at a time
    is_default      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**Available Embedding Models:**

| Model | Provider | Dimensions | Max Input | Cost/1K tokens | Best For |
|-------|----------|-----------|------------|-----------------|----------|
| text-embedding-3-small | OpenAI | 1536 | 8191 | $0.00002 | General purpose, balanced quality |
| bge-large-en-v1.5 | BAAI | 1024 | 512 | Free (self-hosted) | English-focused, high quality |
| bge-m3 | BAAI | 1024 | 8192 | Free (self-hosted) | Multilingual, long documents |

### 8.2 Default Configuration

```
Default Embedding Model: text-embedding-3-small (1536 dims)

Lý do chọn default:
1. Tương thích tốt với pgvector (vector operations optimized cho 1536 dims)
2. Chất lượng tốt cho semantic search
3. Max input tokens cao (8191), phù hợp cho mentor_instructions dài
4. Chi phí rất thấp
5. OpenAI API ổn định và reliable
```

---

## Appendix A: Error Handling Summary

| Error Type | Action | Retry | Fallback |
|-----------|--------|-------|----------|
| Network Timeout | Log → Retry | 3x with backoff | Next model in chain |
| Rate Limit (429) | Log → Backoff → Retry | 3x with longer backoff | Next model in chain |
| Auth Error (401/403) | Log → Alert → Stop | No | No (configuration issue) |
| Server Error (5xx) | Log → Retry | 3x with backoff | Next model in chain |
| Invalid Response | Log → Retry once | 1x | Next model in chain |
| Context Overflow | Summarize or escalate | No | Larger context model |

## Appendix B: Configuration Reference

```yaml
# config/llm.yaml

llm:
  gateway:
    rate_limit_per_minute: 60
    concurrent_requests: 10
    request_timeout_seconds: 120

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 30
    half_open_max_requests: 1

  retry:
    max_retries: 3
    backoff_base_seconds: 1
    backoff_max_seconds: 10

  models:
    deepseek-v4-flash:
      provider: deepseek
      context_window: 64000
      effective_input_limit: 4096
      output_reserve: 1024
      pricing:
        input_per_m: 0.10
        output_per_m: 0.30

    deepseek-v4-pro:
      provider: deepseek
      context_window: 128000
      effective_input_limit: 8192
      output_reserve: 2048
      pricing:
        input_per_m: 0.50
        output_per_m: 1.50

    qwen-3.5-plus:
      provider: qwen
      context_window: 128000
      effective_input_limit: 8192
      output_reserve: 2048
      pricing:
        input_per_m: 0.30
        output_per_m: 0.90

    qwen-3.6-plus:
      provider: qwen
      context_window: 256000
      effective_input_limit: 16384
      output_reserve: 4096
      pricing:
        input_per_m: 0.80
        output_per_m: 2.40

  embedding:
    default_model: text-embedding-3-small
    dimensions: 1536
    similarity_threshold: 0.7
    search_limit: 10

  cost:
    warning_threshold_usd: 5.00
    critical_threshold_usd: 20.00
    blocked_threshold_usd: 50.00
    monthly_limit_usd: 1000.00
```

---

*Document version: 3.0*
*Last updated: 2026-05-15*
*Maintained by: AI SDLC System Architecture Team*
*Key Change from v2: FastAPI LLM Gateway with 2 paths (LiteLLM + OpenCode), not OpenCode-only*
