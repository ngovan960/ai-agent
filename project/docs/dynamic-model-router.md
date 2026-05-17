# Dynamic Model Router

## AI SDLC Orchestrator — Model Selection Strategy

---

## Overview

The Dynamic Model Router selects the best LLM model for each task based on a `TaskProfile` that includes complexity, risk level, and domain. It considers model capabilities, costs, and circuit breaker state.

**File**: `shared/config/model_router.py`

---

## TaskProfile

```python
class TaskProfile:
    complexity: int          # 1-10
    risk_level: str          # LOW, MEDIUM, HIGH, CRITICAL
    domain: str              # "coding", "analysis", "review", "planning"
    max_cost_usd: float      # Budget limit
    latency_requirement: str # "fast", "normal", "thorough"
```

---

## Available Models

| Model | Provider | Context | Input Cost | Output Cost | Strengths |
|-------|----------|---------|------------|-------------|-----------|
| deepseek-v4-flash | DeepSeek | 128K | $0.0001/1K | $0.0002/1K | Fast, cheap, good for classification |
| deepseek-v4-pro | DeepSeek | 128K | $0.001/1K | $0.003/1K | Strong coding, tool use |
| qwen-3.5-plus | Qwen | 32K | $0.0005/1K | $0.001/1K | Good review, analysis |
| qwen-3.6-plus | Qwen | 128K | $0.002/1K | $0.006/1K | Strong reasoning, planning |

**File**: `shared/config/models.yaml`

---

## Routing Algorithm

```
1. Build TaskProfile from task metadata
2. Filter models by:
   - Circuit breaker state (skip OPEN models)
   - Cost budget (skip models exceeding max_cost_usd)
   - Context window (skip models too small for task)
3. Score remaining models:
   - Capability match for domain (0-1)
   - Cost efficiency (lower = better)
   - Latency match for requirement
4. Select model with highest composite score
5. If no model available → escalate to human
```

---

## Capability Scores

Each model has capability scores per domain:

| Model | coding | analysis | review | planning | classification |
|-------|--------|----------|--------|----------|----------------|
| deepseek-v4-flash | 0.6 | 0.5 | 0.4 | 0.5 | 0.8 |
| deepseek-v4-pro | 0.9 | 0.7 | 0.7 | 0.7 | 0.6 |
| qwen-3.5-plus | 0.7 | 0.8 | 0.9 | 0.7 | 0.7 |
| qwen-3.6-plus | 0.8 | 0.9 | 0.8 | 0.9 | 0.8 |

**File**: `shared/config/model_capabilities.yaml`

---

## Routing Examples

| Task Profile | Selected Model | Reason |
|-------------|----------------|--------|
| Complexity 2, LOW risk, classification | deepseek-v4-flash | Cheapest, fastest for simple tasks |
| Complexity 8, HIGH risk, coding | deepseek-v4-pro | Best coding capability |
| Complexity 5, MEDIUM risk, review | qwen-3.5-plus | Best review capability, cost-effective |
| Complexity 9, CRITICAL risk, planning | qwen-3.6-plus | Best reasoning, handles complexity |

---

## Circuit Breaker Integration

The router checks circuit breaker state before selecting a model:

- **CLOSED**: Model available
- **OPEN**: Model skipped, fallback considered
- **HALF_OPEN**: Model available with limited calls

If the preferred model's circuit is OPEN, the router selects the next best available model.

---

## Cost Control

The router enforces cost limits:

```python
if model_cost_per_call > task_profile.max_cost_usd:
    skip_model()
```

Cost tracking is logged to `cost_tracking` table for every LLM call.

---

**Version**: 1.0.0
**Last Updated**: 2026-05-17
**Models**: 4
**Domains**: 5
