# LLM Integration

## AI SDLC Orchestrator — OpenCode LLM Gateway

---

## Overview

The system uses **OpenCode as the sole LLM provider**. All LLM calls go through OpenCode, which manages:
1. Model routing and selection
2. Rate limiting and cost tracking
3. Tool execution (bash, edit, write, read, glob, grep)
4. Sandbox environment (Docker containers)

No external LLM libraries (like LiteLLM) are needed.

---

## Architecture

```
Agent Request
    │
    ▼
┌─────────────────────────────────┐
│  LLM Gateway                     │
│                                  │
│  ┌───────────────────────────┐  │
│  │  Dynamic Model Router      │  │ ← Selects model based on TaskProfile
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Circuit Breaker           │  │ ← Per-model circuit breaker
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Retry Handler             │  │ ← Exponential backoff
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  OpenCode LLM Client       │  │ ← All calls via OpenCode API
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  OpenCode API              │  │ ← Manages models, tools, sandbox
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Cost Tracker              │  │ ← Log tokens, cost, latency
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## OpenCode LLM Client

**File**: `services/execution/opencode_llm_client.py`

### Usage

```python
from services.execution.opencode_llm_client import OpenCodeLLMClient

async with OpenCodeLLMClient() as client:
    response = await client.chat_completion(
        model="qwen-3.6-plus",
        messages=[
            {"role": "system", "content": "You are a coding assistant."},
            {"role": "user", "content": "Write a function to sort a list."},
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    print(response.content)
    print(f"Tokens: {response.total_tokens}, Cost: ${response.cost_usd}")
```

### Response Format

```python
@dataclass
class LLMResponse:
    content: str          # Generated text
    model: str            # Model used
    input_tokens: int     # Prompt tokens
    output_tokens: int    # Completion tokens
    total_tokens: int     # Total tokens
    cost_usd: float       # Cost in USD
    latency_ms: float     # Response time
    finish_reason: str    # "stop", "length", "error"
    error: Optional[str]  # Error message if any
```

### Retry Logic
- Max retries: 3 (configurable)
- Exponential backoff: 2s → 4s → 8s (capped at 30s)
- On final failure: returns LLMResponse with error field

---

## Model Assignments (Preferences)

| Agent | Preferred Model | Reason |
|-------|----------------|--------|
| Gatekeeper | DeepSeek V4 Flash | Fast, cheap classification |
| Orchestrator | Qwen 3.6 Plus | Strong reasoning, planning |
| Validator | Qwen 3.5 Plus | Good review capability |
| Specialist | DeepSeek V4 Pro | Best coding, tool use |
| Auditor | Qwen 3.5 Plus | Strong analysis, review |
| Mentor | Qwen 3.6 Plus | Strategic reasoning |
| DevOps | DeepSeek V4 Pro | Tool-enabled deployment |
| Monitoring | MiniMax M2.7 | Fast, cheap monitoring |

> **Note**: These are preferences. The Dynamic Model Router may select different models based on task profile and circuit breaker state.

---

## Available Models

**File**: `shared/config/models.yaml`

| Model | Context | Input Cost | Output Cost | Speed |
|-------|---------|------------|-------------|-------|
| deepseek-v4-flash | 128K | $0.0001/1K tokens | $0.0003/1K tokens | very_fast |
| deepseek-v4-pro | 128K | $0.00043/1K tokens | $0.00087/1K tokens | medium |
| qwen-3.5-plus | 32K | $0.00039/1K tokens | $0.00234/1K tokens | medium |
| qwen-3.6-plus | 128K | $0.00033/1K tokens | $0.00195/1K tokens | slow |
| minimax-m2-7 | 32K | $0.00026/1K tokens | $0.00120/1K tokens | fast |

---

## Cost Tracking

Every LLM call is logged to `cost_tracking` and `llm_call_logs` tables:

```python
{
    "task_id": "uuid",
    "agent_name": "specialist",
    "model": "deepseek-v4-pro",
    "input_tokens": 1500,
    "output_tokens": 800,
    "cost_usd": 0.0039,
    "latency_ms": 2340,
    "status": "completed",
}
```

---

## Environment Variables

```bash
# OpenCode LLM Configuration (sole provider)
OPENCODE_API_URL=http://localhost:8080
OPENCODE_API_KEY=your_opencode_api_key

# OpenCode Tool Execution
OPENCODE_ENABLED=true
OPENCODE_SANDBOX_IMAGE=ai-sdlc-sandbox:latest
```

---

**Version**: 5.0.0
**Last Updated**: 2026-05-17
**Provider**: OpenCode (sole)
**Models**: 5
