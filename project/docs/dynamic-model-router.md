# Dynamic Model Router — AI SDLC System

## Metadata

- **Version**: 4.2.0
- **Created**: 2026-05-15
- **Last Updated**: 2026-05-15
- **Related**: [ARCHITECTURE.md](../ARCHITECTURE.md), [llm-integration.md](./llm-integration.md), [opencode-architecture.md](./opencode-architecture.md)
- **Key Change from v4.1**: Added Context Window Management (section 4.6) with "Lost in the Middle" mitigation, priority-based truncation

---

## 1. Overview

Hệ thống **không gán cố định** model cho agent. Thay vào đó, **Dynamic Model Router** tự động chọn model phù hợp nhất dựa trên:

1. **Task profile** — Loại task, độ phức tạp, context size cần thiết, yêu cầu tốc độ
2. **Model capabilities** — Điểm mạnh/yếu của từng model (code, reasoning, speed, cost)
3. **Cost constraints** — Budget available cho task
4. **Context fit** — Model có đủ context window cho task không
5. **Circuit breaker state** — Model có đang bị circuit breaker open không

### Tại sao Dynamic Routing?

| Vấn đề của Fixed Mapping | Giải pháp của Dynamic Routing |
|---|---|
| Model A giỏi code nhưng bị gán cho review | Router chọn model giỏi nhất cho từng task type |
| Model đắt tiền dùng cho task đơn giản | Router chọn model rẻ nhất đủ khả năng |
| Model fail nhưng không có fallback tự động | Router tự động fallback sang model khác |
| Không tận dụng được model mới | Router tự động tích hợp model mới vào registry |

---

## 2. Model Capability Registry

### 2.1 Danh sách Models (5 models)

| Model | Provider | Code Rank | Math Rank | Text Rank | Context | Cost ($/M in/out) | Speed |
|---|---|---|---|---|---|---|---|
| **DeepSeek V4 Flash** | DeepSeek | — | — | — | 131K | $0.10 / $0.30 | Rất nhanh |
| **DeepSeek V4 Pro** | DeepSeek | 30 | 48 | 30 | 1M | $0.43 / $0.87 | Trung bình |
| **Qwen 3.5 Plus** | Alibaba | 38 | 39 | 49 | 262K | $0.39 / $2.34 | Trung bình |
| **Qwen 3.6 Plus** | Alibaba | 14 | 19 | 48 | 1M | $0.33 / $1.95 | Chậm |
| **MiniMax M2.7** | MiniMax | 27 | — | — | 196K | $0.26 / $1.20 | Nhanh |

### 2.2 Capability Scores (0-100)

| Model | Code | Reasoning | Classification | Review | Planning | Speed | Cost Efficiency |
|---|---|---|---|---|---|---|---|
| **DeepSeek V4 Flash** | 40 | 35 | 70 | 35 | 30 | 95 | 95 |
| **DeepSeek V4 Pro** | 75 | 65 | 70 | 65 | 60 | 60 | 85 |
| **Qwen 3.5 Plus** | 65 | 65 | 60 | 70 | 65 | 55 | 60 |
| **Qwen 3.6 Plus** | 80 | 80 | 55 | 75 | 85 | 35 | 75 |
| **MiniMax M2.7** | 70 | 60 | 65 | 60 | 55 | 80 | 90 |

### 2.3 Model Strengths & Weaknesses

```yaml
deepseek_v4_flash:
  strengths:
    - "Fastest response time"
    - "Lowest cost per token"
    - "Good for simple classification tasks"
  weaknesses:
    - "Limited context window (131K)"
    - "Weak at complex reasoning"
    - "Not suitable for code generation"
  best_for: ["classification", "routing", "simple_tasks", "monitoring"]
  avoid_for: ["code_generation", "strategic_reasoning", "complex_review"]

deepseek_v4_pro:
  strengths:
    - "Strong code generation"
    - "Large context window (1M)"
    - "Very cost-effective for capability"
    - "Balanced across tasks"
  weaknesses:
    - "Math reasoning weaker than peers"
    - "Slower than Flash"
  best_for: ["code_generation", "implementation", "devops", "fallback"]
  avoid_for: ["strategic_decisions", "complex_math"]

qwen_3_5_plus:
  strengths:
    - "Good at code review and analysis"
    - "Balanced capabilities"
    - "Reasonable cost"
  weaknesses:
    - "Not exceptional in any area"
    - "Slower than Flash and MiniMax"
    - "Context window limited (262K)"
  best_for: ["code_review", "quality_assurance", "analysis"]
  avoid_for: ["fast_classification", "large_context_tasks"]

qwen_3_6_plus:
  strengths:
    - "Best strategic reasoning"
    - "Best at planning and orchestration"
    - "Large context window (1M)"
    - "Good at complex decisions"
  weaknesses:
    - "Slowest response time"
    - "Instruction following weaker than expected"
    - "Higher cost for long outputs"
  best_for: ["strategic_reasoning", "planning", "mentor_decisions", "orchestration"]
  avoid_for: ["fast_classification", "simple_tasks", "cost_sensitive_tasks"]

minimax_m2_7:
  strengths:
    - "Good code generation capability"
    - "Fast response time"
    - "Very cost-effective"
    - "Reasonable context window (196K)"
  weaknesses:
    - "Less proven in production"
    - "Text/math benchmarks unknown"
    - "Smaller ecosystem"
  best_for: ["monitoring", "continuous_tasks", "cost_sensitive_code", "fallback"]
  avoid_for: ["strategic_decisions", "complex_review"]
```

---

## 3. Task Profiler

### 3.1 Task Profile Schema

```python
@dataclass
class TaskProfile:
    task_type: str           # "classification", "code_generation", "review", "planning", "decision", "monitoring"
    complexity: int          # 1-10
    context_size: str        # "small" (<4K), "medium" (4K-32K), "large" (32K-128K), "huge" (>128K)
    speed_requirement: str   # "fast", "balanced", "thorough"
    budget_usd: float        # Available budget for this task
    is_retry: bool           # Is this a retry attempt?
    previous_model: str      # Model used in previous attempt (if retry)
    requires_tools: bool     # Does this task need tool execution (bash, edit, write)?
    priority: str            # "LOW", "MEDIUM", "HIGH", "CRITICAL"
```

### 3.2 Task Type Detection

```python
TASK_TYPE_RULES = {
    "classification": {
        "keywords": ["classify", "categorize", "route", "identify", "parse"],
        "max_complexity": 5,
        "typical_context": "small",
    },
    "code_generation": {
        "keywords": ["implement", "create", "build", "write code", "develop", "module", "feature"],
        "max_complexity": 10,
        "typical_context": "medium",
    },
    "review": {
        "keywords": ["review", "audit", "check", "verify", "assess", "quality"],
        "max_complexity": 8,
        "typical_context": "medium",
    },
    "planning": {
        "keywords": ["plan", "break down", "design", "architect", "organize", "schedule"],
        "max_complexity": 10,
        "typical_context": "large",
    },
    "decision": {
        "keywords": ["decide", "resolve", "escalate", "strategic", "conflict", "deadlock"],
        "max_complexity": 10,
        "typical_context": "large",
    },
    "monitoring": {
        "keywords": ["monitor", "track", "observe", "alert", "detect", "analyze logs"],
        "max_complexity": 6,
        "typical_context": "small",
    },
}
```

---

## 4. Routing Algorithm

### 4.1 Scoring Formula

```
Score(model, task) =
    capability_match(task_type, model) * 0.40
    + context_fit(task.context_size, model.context_window) * 0.20
    + speed_match(task.speed_requirement, model.speed) * 0.15
    + cost_efficiency(model, task.budget) * 0.15
    + circuit_breaker_bonus(model) * 0.10
```

### 4.2 Scoring Details

```python
def score_model(model: Model, task: TaskProfile) -> float:
    # 1. Capability match (40%)
    capability = model.capabilities.get(task.task_type, 0) / 100.0

    # 2. Context fit (20%)
    context_needed = CONTEXT_SIZE_MAP[task.context_size]
    context_fit = min(1.0, model.context_window / context_needed)
    if context_needed > model.context_window:
        context_fit = 0.0  # Cannot handle this task

    # 3. Speed match (15%)
    speed_score = SPEED_MATCH_MAP.get(
        (task.speed_requirement, model.speed_category), 0.5
    )

    # 4. Cost efficiency (15%)
    cost_per_token = (model.input_cost + model.output_cost) / 2
    cost_score = max(0.0, 1.0 - (cost_per_token / MAX_COST_PER_TOKEN))

    # 5. Circuit breaker bonus (10%)
    cb_state = get_circuit_breaker_state(model.name)
    cb_bonus = 1.0 if cb_state == "closed" else 0.0

    score = (
        capability * 0.40
        + context_fit * 0.20
        + speed_score * 0.15
        + cost_score * 0.15
        + cb_bonus * 0.10
    )

    return score
```

### 4.3 Routing Decision

```python
def select_model(task: TaskProfile) -> ModelSelection:
    # 1. Filter out models that cannot handle the task
    candidates = [
        m for m in ALL_MODELS
        if m.context_window >= CONTEXT_SIZE_MAP[task.context_size]
        and get_circuit_breaker_state(m.name) != "open"
    ]

    if not candidates:
        # All models unavailable — escalate
        raise NoModelAvailableError("All models are unavailable")

    # 2. Score each candidate
    scored = [(m, score_model(m, task)) for m in candidates]

    # 3. Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # 4. Return top model + fallback chain
    primary = scored[0][0]
    fallbacks = [m for m, _ in scored[1:3]]  # Next 2 best models

    return ModelSelection(
        primary=primary,
        fallbacks=fallbacks,
        llm_path="opencode" if task.requires_tools else "litellm",
        estimated_cost=estimate_cost(primary, task),
    )
```

### 4.4 Default Routing Table (when scoring not available)

| Task Type | Primary Model | Fallback 1 | Fallback 2 | LLM Path |
|---|---|---|---|---|
| **classification** | DeepSeek V4 Flash | MiniMax M2.7 | DeepSeek V4 Pro | LiteLLM |
| **validation** | Qwen 3.5 Plus | Qwen 3.6 Plus | DeepSeek V4 Pro | LiteLLM |
| **code_generation** | DeepSeek V4 Pro | Qwen 3.6 Plus | MiniMax M2.7 | OpenCode |
| **review** | Qwen 3.5 Plus | Qwen 3.6 Plus | DeepSeek V4 Pro | LiteLLM |
| **planning** | Qwen 3.6 Plus | DeepSeek V4 Pro | Qwen 3.5 Plus | LiteLLM |
| **decision** | Qwen 3.6 Plus | DeepSeek V4 Pro | MiniMax M2.7 | LiteLLM |
| **monitoring** | MiniMax M2.7 | DeepSeek V4 Flash | Qwen 3.5 Plus | LiteLLM |

---

## 4.5 Dual-Model Validation Gate

### Tại sao cần Validation Gate?

Gatekeeper phân loại task một mình — nếu sai, sai lầm lan truyền xuống toàn bộ pipeline. Validation gate thêm lớp kiểm duyệt ngay từ bước đầu.

### Quy trình

```
User request → Gatekeeper (DeepSeek V4 Flash) → Classification
                    ↓
              Validator (Qwen 3.5 Plus) → Cross-validate classification
                    ↓
              Match + confidence ≥ 0.8 → Pass to Orchestrator
              Match + confidence < 0.8 → Gatekeeper re-analyze
              Mismatch → Escalate to Mentor (Qwen 3.6 Plus)
```

### Model Allocation cho Validation

| Role | Model | Lý do | Cost |
|---|---|---|---|
| Gatekeeper | DeepSeek V4 Flash | Nhanh, rẻ, phân loại cơ bản | ~$0.0001/call |
| Validator | Qwen 3.5 Plus | Reasoning tốt, phát hiện lỗi classification | ~$0.001/call |
| Tie-breaker | Qwen 3.6 Plus | Khi 2 model conflict | ~$0.002/call |

### Khi nào Validator trigger?

| Risk Level | Complexity | Require Validator | Require Mentor |
|---|---|---|---|
| LOW | TRIVIAL | No | No |
| LOW | SIMPLE | No | No |
| MEDIUM | MEDIUM | Yes | No |
| HIGH | COMPLEX | Yes | Yes |
| CRITICAL | CRITICAL | Yes | Yes + Human |

### Validation Decision Matrix

| Validator Verdict | Confidence | Action |
|---|---|---|
| APPROVED | ≥ 0.8 | Pass to Orchestrator |
| APPROVED | < 0.8 | Gatekeeper re-analyze |
| NEEDS_REVIEW | ≥ 0.5 | Gatekeeper re-analyze |
| NEEDS_REVIEW | < 0.5 | Escalate to Mentor |
| REJECTED | Any | Escalate to Mentor (HIGH/CRITICAL) hoặc Gatekeeper re-analyze |

### API Endpoints

```
POST /api/v1/validation/          — Full validation with classification
POST /api/v1/validation/quick     — Quick validation with params
GET  /api/v1/validation/should-skip — Check if validation can be skipped
```

### State Transition Impact

Điều kiện NEW → ANALYZING được cập nhật:
- **Trước**: Gatekeeper đã phân loại task
- **Sau**: Gatekeeper đã phân loại + **Validator đã approve** (trừ risk=low AND complexity=trivial/simple)

```python
# state_transitions.py v3
def validate_transition_with_gatecheck(
    current_status, new_status,
    has_validated=False,
    risk_level="low",
    complexity="simple",
):
    if current_status == "NEW" and new_status == "ANALYZING":
        if requires_validation(risk_level, complexity) and not has_validated:
            return False, "Requires dual-model validation approval"
    return validate_transition(current_status, new_status)
```

---

## 4.6 Context Window Management (v4.1)

### "Lost in the Middle" Phenomenon

Research (Liu et al., 2023) shows that LLMs pay most attention to:
- **First ~20%** of context window
- **Last ~20%** of context window
- **Least attention**: middle ~60%

This means critical information placed in the middle of a large context may be ignored.

### Mitigation Strategy

The `ContextBuilder` service implements a three-zone attention optimization:

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT WINDOW                            │
├─────────────────┬───────────────────┬───────────────────────┤
│   BEGINNING     │      MIDDLE       │        END            │
│   (P ≥ 80)      │   (P 40-79)       │     (P < 40)          │
│   HIGH ATTENTION│   MED ATTENTION   │   MED-HIGH ATTENTION  │
├─────────────────┼───────────────────┼───────────────────────┤
│ Task Desc (100) │ Memory (50)       │ Laws (30)             │
│ Output fmt (90) │ Module specs (40) │ Codebase (20)         │
│ System prompt   │                   │ Audit logs (10)       │
│ Self-aware (70) │                   │                       │
│ Validation (60) │                   │                       │
└─────────────────┴───────────────────┴───────────────────────┘
```

### Priority Levels

| Priority | Section | Zone | Truncation Order |
|---|---|---|---|
| 100 | Task description | Beginning | Last (never truncated) |
| 90 | Output format | Beginning | Last |
| 80 | System prompt | Beginning | Last |
| 70 | Self-awareness | Beginning | Late |
| 60 | Validation results | Beginning | Late |
| 50 | Relevant memory | Middle | Medium |
| 40 | Module specs | Middle | Medium |
| 30 | Architectural laws | End | Early |
| 20 | Full codebase | End | Early |
| 10 | Historical logs | End | First |

### Implementation

```python
from services.orchestrator.services.context_builder import ContextBuilder

builder = ContextBuilder(max_tokens=128000, safety_margin=4096)

# Critical info — always at beginning
builder.add_section("Task Description", task_desc, priority=100)
builder.add_section("Output Format", output_fmt, priority=90)
builder.add_section("Agent Role", system_prompt, priority=80)

# Medium priority — in middle
builder.add_section("Relevant Memory", memory, priority=50)
builder.add_section("Module Specs", specs, priority=40)

# Lower priority — at end
builder.add_section("Architectural Laws", laws, priority=30)

context = builder.build()
# Automatically reordered: beginning → middle → end
# Truncated if exceeds max_tokens
```

### Context Overflow Protocol

When context still exceeds limit after priority truncation:
1. Log overflow event with token counts
2. Escalate task — request user to split into smaller tasks
3. Force switch to model with larger context (Qwen 3.6 Plus: 1M tokens)
4. Reduce context — keep only task description + essential info

---

## 5. Self-Awareness System

### 5.1 Model Self-Awareness Prompt

Mỗi model khi được gọi nhận system prompt cho biết:

```
[SYSTEM: AI SDLC Agent]
You are the {agent_name} agent in the AI SDLC System.

## Your Identity
- Agent role: {role_description}
- Your model: {model_name} ({model_provider})
- Your strengths: {model_strengths}
- Your limitations: {model_limitations}

## Current Task
- Task ID: {task_id}
- Task title: {task_title}
- Task state: {task_state}
- Priority: {priority}

## Your Responsibility
{specific_responsibilities}

## What You MUST NOT Do
- {restriction_1}
- {restriction_2}
- {restriction_3}

## Handoff Protocol
If you cannot complete this task:
1. Output: #ESCALATE with reason
2. Do NOT attempt tasks outside your capability
3. Do NOT modify state directly — report to orchestrator

## Next Agent in Pipeline
After you complete your work, the task goes to: {next_agent}

## Architectural Laws
{laws_subset}

## Output Format
{output_schema}
[/SYSTEM]
```

### 5.2 Self-Awareness by Agent

```yaml
gatekeeper:
  role: "Classification and routing specialist"
  strengths: "Fast, accurate at categorizing requests"
  limitations: "Cannot write code, cannot make strategic decisions"
  must_not:
    - "Write or modify code"
    - "Make architectural decisions"
    - "Execute commands"
  handoff_to: "orchestrator (if complexity > 3) or direct to specialist (if simple)"

orchestrator:
  role: "Task breakdown and workflow planning"
  strengths: "Strategic reasoning, long context understanding"
  limitations: "Cannot write code, cannot execute commands"
  must_not:
    - "Write or modify code"
    - "Execute commands"
    - "Make final decisions on escalated tasks"
  handoff_to: "specialist (for implementation), auditor (for review)"

specialist:
  role: "Code generation and implementation"
  strengths: "Strong code generation, tool execution"
  limitations: "Should not make architectural changes, should not review own code"
  must_not:
    - "Change architecture without approval"
    - "Review own code"
    - "Deploy to production"
    - "Add features beyond task scope"
  handoff_to: "verification pipeline (after implementation)"

auditor:
  role: "Code review and quality assurance"
  strengths: "Analytical thinking, attention to detail"
  limitations: "Cannot write code, cannot execute commands"
  must_not:
    - "Write or modify code"
    - "Execute commands (except running tests)"
    - "Approve code with critical law violations"
  handoff_to: "specialist (if revise), mentor (if escalate)"

mentor:
  role: "Strategic decision maker for escalated tasks"
  strengths: "Best reasoning capability, handles complex decisions"
  limitations: "Cannot write code, cannot execute commands"
  must_not:
    - "Write or modify code"
    - "Bypass verification without strong reason"
    - "Retry after verdict — decision is final"
  handoff_to: "none (final decision)"

devops:
  role: "Build, deploy, and infrastructure management"
  strengths: "Strong at deployment, CI/CD, infrastructure"
  limitations: "Cannot modify application code"
  must_not:
    - "Modify application source code"
    - "Deploy to production without approval"
    - "Skip health checks"
  handoff_to: "monitoring (after deployment)"

monitoring:
  role: "Continuous observation and alerting"
  strengths: "Fast, cost-effective for continuous tasks"
  limitations: "Cannot modify code, cannot make decisions"
  must_not:
    - "Modify code or configuration"
    - "Make strategic decisions"
    - "Deploy changes"
  handoff_to: "orchestrator (if anomaly detected)"
```

---

## 6. Conflict Prevention

### 6.1 Role-Boundary Enforcement

```
Agent A ──→ Output A ──→ Validation ──→ Agent B
                    ↑                        ↑
              Agent A's role           Agent B's role
              boundary check           boundary check
```

Mỗi agent chỉ được phép:
- **Input**: Nhận data từ agent trước trong pipeline
- **Output**: Trả data cho agent sau trong pipeline
- **Tools**: Chỉ dùng tools được phép (theo tool permission matrix)
- **State**: Chỉ trigger transitions được phép (theo state machine)

### 6.2 State-Gated Execution

```python
async def execute_agent(agent_name: str, task_id: str) -> AgentResult:
    # 1. Check task state matches agent's expected state
    task = await get_task(task_id)
    expected_state = AGENT_STATE_MAP[agent_name]

    if task.status not in expected_state:
        raise StateMismatchError(
            f"Agent {agent_name} expects state in {expected_state}, "
            f"but task is in {task.status}"
        )

    # 2. Check agent has permission for this task type
    if not agent_can_handle(agent_name, task.task_type):
        raise PermissionError(
            f"Agent {agent_name} cannot handle task type {task.task_type}"
        )

    # 3. Execute agent
    result = await call_agent(agent_name, task)

    # 4. Validate output before handoff
    validated = await validate_agent_output(agent_name, result)

    return validated
```

### 6.3 Handoff Protocol

```
Agent A completes work
    │
    ├── Output validation
    │   ├── Format check (JSON schema)
    │   ├── Content check (not empty, not malformed)
    │   └── Law check (no violations)
    │
    ├── If validation fails
    │   ├── Retry Agent A (if retries left)
    │   └── Escalate to Mentor (if max retries)
    │
    └── If validation passes
        ├── Create audit log
        ├── Update task state
        └── Handoff to Agent B
```

---

## 7. Fallback Chain

### 7.1 Fallback Rules

```yaml
fallback_rules:
  deepseek_v4_flash:
    fallback_1: "minimax_m2_7"
    fallback_2: "deepseek_v4_pro"
    reason: "If Flash fails, try MiniMax (similar speed), then Pro (more capable)"

  deepseek_v4_pro:
    fallback_1: "qwen_3_6_plus"
    fallback_2: "minimax_m2_7"
    reason: "If Pro fails, try Qwen 3.6 (stronger reasoning), then MiniMax (cheaper)"

  qwen_3_5_plus:
    fallback_1: "qwen_3_6_plus"
    fallback_2: "deepseek_v4_pro"
    reason: "If 3.5 fails, try 3.6 (same provider, stronger), then Pro (balanced)"

  qwen_3_6_plus:
    fallback_1: "deepseek_v4_pro"
    fallback_2: "minimax_m2_7"
    reason: "If 3.6 fails, try Pro (capable), then MiniMax (fast)"

  minimax_m2_7:
    fallback_1: "deepseek_v4_pro"
    fallback_2: "qwen_3_5_plus"
    reason: "If MiniMax fails, try Pro (proven), then 3.5 (balanced)"
```

### 7.2 Fallback Execution

```python
async def call_with_fallback(
    agent_name: str,
    task_data: dict,
    model_selection: ModelSelection,
) -> AgentResult:
    # Try primary model
    try:
        return await call_agent(agent_name, task_data, model_selection.primary)
    except (TimeoutError, RateLimitError, ServerError) as e:
        log_model_failure(model_selection.primary.name, e)

    # Try fallback 1
    if model_selection.fallbacks:
        try:
            return await call_agent(
                agent_name, task_data, model_selection.fallbacks[0]
            )
        except (TimeoutError, RateLimitError, ServerError) as e:
            log_model_failure(model_selection.fallbacks[0].name, e)

    # Try fallback 2
    if len(model_selection.fallbacks) > 1:
        try:
            return await call_agent(
                agent_name, task_data, model_selection.fallbacks[1]
            )
        except (TimeoutError, RateLimitError, ServerError) as e:
            log_model_failure(model_selection.fallbacks[1].name, e)

    # All models failed — escalate
    raise AllModelsFailedError(
        f"All models failed for agent {agent_name}"
    )
```

---

## 8. Cost-Aware Routing

### 8.1 Budget-Aware Selection

```python
def select_model_within_budget(task: TaskProfile, budget_usd: float) -> ModelSelection:
    candidates = [
        m for m in ALL_MODELS
        if estimate_cost(m, task) <= budget_usd
        and m.context_window >= CONTEXT_SIZE_MAP[task.context_size]
    ]

    if not candidates:
        # Relax budget constraint — pick cheapest available
        candidates = [
            m for m in ALL_MODELS
            if m.context_window >= CONTEXT_SIZE_MAP[task.context_size]
        ]

    scored = [(m, score_model(m, task)) for m in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    return ModelSelection(
        primary=scored[0][0],
        fallbacks=[m for m, _ in scored[1:3]],
    )
```

### 8.2 Cost Estimates per Task Type

| Task Type | Avg Input Tokens | Avg Output Tokens | Cheapest Model Cost | Most Expensive Model Cost |
|---|---|---|---|---|
| Classification | 500 | 200 | $0.0001 (Flash) | $0.0007 (Qwen 3.6) |
| Code Generation | 4000 | 3000 | $0.0013 (MiniMax) | $0.0071 (Qwen 3.6) |
| Review | 6000 | 1000 | $0.0018 (Qwen 3.5) | $0.0026 (Qwen 3.6) |
| Planning | 8000 | 2000 | $0.0033 (Qwen 3.6) | $0.0045 (Qwen 3.6) |
| Decision | 10000 | 1500 | $0.0038 (Qwen 3.6) | $0.0052 (Qwen 3.6) |
| Monitoring | 1000 | 500 | $0.0002 (MiniMax) | $0.0005 (Qwen 3.6) |

---

## 9. Integration with FastAPI LLM Gateway

### 9.1 Gateway Flow

```
FastAPI Agent Request
    │
    ▼
Task Profiler ──→ Build TaskProfile
    │
    ▼
Model Router ──→ Score all models → Select best → Return ModelSelection
    │
    ▼
Circuit Breaker Check ──→ Is primary model available?
    │
    ├── Yes → Call primary model
    │
    └── No → Try fallback 1 → Try fallback 2 → Escalate
    │
    ▼
Response Parser ──→ Validate output
    │
    ├── Valid → Return to agent
    │
    └── Invalid → Retry with same model (1 attempt) → Fallback
    │
    ▼
Cost Tracker ──→ Log cost, update budget
    │
    ▼
Audit Logger ──→ Log model selection, fallback used, cost
```

### 9.2 Gateway API

```python
# FastAPI LLM Gateway
class LLMGateway:
    async def call_agent(
        self,
        agent_name: str,
        task_data: dict,
        budget_usd: float = None,
    ) -> AgentResult:
        # 1. Profile the task
        profile = self.task_profiler.profile(task_data)

        # 2. Select model (with or without budget constraint)
        if budget_usd:
            selection = self.model_router.select_within_budget(
                profile, budget_usd
            )
        else:
            selection = self.model_router.select(profile)

        # 3. Execute with fallback
        result = await self.call_with_fallback(
            agent_name, task_data, selection
        )

        # 4. Log everything
        await self.log_call(profile, selection, result)

        return result
```

---

## 10. Monitoring & Feedback Loop

### 10.1 Model Performance Tracking

```sql
-- Track model performance per task type
CREATE TABLE model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    success_rate FLOAT NOT NULL DEFAULT 0,
    avg_latency_ms INT NOT NULL DEFAULT 0,
    avg_cost_usd FLOAT NOT NULL DEFAULT 0,
    total_calls INT NOT NULL DEFAULT 0,
    total_failures INT NOT NULL DEFAULT 0,
    total_fallbacks INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),

    UNIQUE (model_name, task_type, agent_name)
);
```

### 10.2 Adaptive Routing (Future)

Sau khi thu thập đủ data, hệ thống có thể tự động điều chỉnh capability scores:

```python
def update_capability_scores():
    """
    Adjust model capability scores based on actual performance data.
    If a model consistently performs well on code generation,
    increase its code score. If it performs poorly, decrease.
    """
    for model in ALL_MODELS:
        for task_type in TASK_TYPES:
            perf = get_model_performance(model.name, task_type)
            if perf.total_calls > 100:  # Minimum sample size
                current_score = model.capabilities[task_type]
                actual_score = perf.success_rate * 100
                # Slowly adjust towards actual performance
                model.capabilities[task_type] = (
                    current_score * 0.9 + actual_score * 0.1
                )
```

---

## Metadata

- **Version**: 4.0.0
- **Created**: 2026-05-15
- **Last Updated**: 2026-05-15
- **Status**: Design complete — ready for implementation in Phase 3
