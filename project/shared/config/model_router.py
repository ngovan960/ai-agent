"""
Dynamic Model Router - AI SDLC System v4

Selects the best LLM model for each task based on:
- Task profile (type, complexity, context size, speed needs)
- Model capabilities (code, reasoning, classification, review, planning)
- Cost constraints
- Circuit breaker state

Version: 4.0.0
Created: 2026-05-15
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    CODE_GENERATION = "code_generation"
    REVIEW = "review"
    PLANNING = "planning"
    DECISION = "decision"
    MONITORING = "monitoring"


class ContextSize(str, Enum):
    SMALL = "small"       # <4K tokens
    MEDIUM = "medium"     # 4K-32K tokens
    LARGE = "large"       # 32K-128K tokens
    HUGE = "huge"         # >128K tokens


class SpeedRequirement(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    THOROUGH = "thorough"


class SpeedCategory(str, Enum):
    VERY_FAST = "very_fast"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class LLMPath(str, Enum):
    LITELLM = "litellm"
    OPENCODE = "opencode"


CONTEXT_SIZE_TOKENS = {
    ContextSize.SMALL: 4096,
    ContextSize.MEDIUM: 32768,
    ContextSize.LARGE: 131072,
    ContextSize.HUGE: 524288,
}

SPEED_MATCH_SCORE = {
    (SpeedRequirement.FAST, SpeedCategory.VERY_FAST): 1.0,
    (SpeedRequirement.FAST, SpeedCategory.FAST): 0.9,
    (SpeedRequirement.FAST, SpeedCategory.MEDIUM): 0.5,
    (SpeedRequirement.FAST, SpeedCategory.SLOW): 0.2,
    (SpeedRequirement.BALANCED, SpeedCategory.VERY_FAST): 0.7,
    (SpeedRequirement.BALANCED, SpeedCategory.FAST): 0.8,
    (SpeedRequirement.BALANCED, SpeedCategory.MEDIUM): 1.0,
    (SpeedRequirement.BALANCED, SpeedCategory.SLOW): 0.6,
    (SpeedRequirement.THOROUGH, SpeedCategory.VERY_FAST): 0.4,
    (SpeedRequirement.THOROUGH, SpeedCategory.FAST): 0.5,
    (SpeedRequirement.THOROUGH, SpeedCategory.MEDIUM): 0.8,
    (SpeedRequirement.THOROUGH, SpeedCategory.SLOW): 1.0,
}

MAX_COST_PER_TOKEN = 0.005  # $5 per 1K tokens (upper bound for normalization)


@dataclass
class TaskProfile:
    task_type: TaskType
    complexity: int = 5
    context_size: ContextSize = ContextSize.MEDIUM
    speed_requirement: SpeedRequirement = SpeedRequirement.BALANCED
    budget_usd: float = 1.0
    is_retry: bool = False
    previous_model: Optional[str] = None
    requires_tools: bool = False
    priority: str = "MEDIUM"


@dataclass
class Model:
    name: str
    provider: str
    context_window: int
    max_output_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    timeout_seconds: int
    speed_category: SpeedCategory
    capabilities: dict = field(default_factory=dict)
    strengths: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    best_for: list = field(default_factory=list)
    avoid_for: list = field(default_factory=list)


@dataclass
class ModelSelection:
    primary: Model
    fallbacks: list = field(default_factory=list)
    llm_path: LLMPath = LLMPath.LITELLM
    estimated_cost: float = 0.0
    estimated_tokens: int = 0


class ModelRouter:
    """Dynamic model router for AI SDLC System."""

    def __init__(self, models: list[Model]):
        self.models = models
        self._circuit_breaker_state: dict[str, str] = {}

    def set_circuit_breaker_state(self, model_name: str, state: str):
        """Set circuit breaker state for a model: closed, open, half_open."""
        self._circuit_breaker_state[model_name] = state

    def get_circuit_breaker_state(self, model_name: str) -> str:
        """Get circuit breaker state for a model."""
        return self._circuit_breaker_state.get(model_name, "closed")

    def select(self, task: TaskProfile) -> ModelSelection:
        """Select best model for a task using scoring algorithm."""
        # Filter out models with open circuit breaker
        candidates = [
            m for m in self.models
            if self.get_circuit_breaker_state(m.name) != "open"
        ]

        if not candidates:
            raise NoModelAvailableError("All models have open circuit breakers")

        # Filter out models that cannot handle context size
        context_needed = CONTEXT_SIZE_TOKENS[task.context_size]
        candidates = [
            m for m in candidates
            if m.context_window >= context_needed
        ]

        if not candidates:
            # Relax context constraint — pick model with largest context
            candidates = sorted(
                self.models,
                key=lambda m: m.context_window,
                reverse=True,
            )
            candidates = [
                m for m in candidates
                if self.get_circuit_breaker_state(m.name) != "open"
            ]

        if not candidates:
            raise NoModelAvailableError("No models available for this task")

        # Score each candidate
        scored = [(m, self._score_model(m, task)) for m in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select primary and fallbacks
        primary = scored[0][0]
        fallbacks = [m for m, _ in scored[1:3]]

        # Determine LLM path
        llm_path = LLMPath.OPENCODE if task.requires_tools else LLMPath.LITELLM

        # Estimate cost
        estimated_tokens = self._estimate_tokens(task)
        estimated_cost = self._estimate_cost(primary, task)

        return ModelSelection(
            primary=primary,
            fallbacks=fallbacks,
            llm_path=llm_path,
            estimated_cost=estimated_cost,
            estimated_tokens=estimated_tokens,
        )

    def select_within_budget(
        self, task: TaskProfile, budget_usd: float
    ) -> ModelSelection:
        """Select best model within budget constraint."""
        candidates = [
            m for m in self.models
            if self._estimate_cost(m, task) <= budget_usd
            and self.get_circuit_breaker_state(m.name) != "open"
        ]

        if not candidates:
            # Relax budget — just pick best available
            return self.select(task)

        scored = [(m, self._score_model(m, task)) for m in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        primary = scored[0][0]
        fallbacks = [m for m, _ in scored[1:3]]
        llm_path = LLMPath.OPENCODE if task.requires_tools else LLMPath.LITELLM

        return ModelSelection(
            primary=primary,
            fallbacks=fallbacks,
            llm_path=llm_path,
            estimated_cost=self._estimate_cost(primary, task),
            estimated_tokens=self._estimate_tokens(task),
        )

    def _score_model(self, model: Model, task: TaskProfile) -> float:
        """Score a model for a given task (0-1)."""
        # 1. Capability match (40%)
        capability = model.capabilities.get(task.task_type.value, 0) / 100.0

        # 2. Context fit (20%)
        context_needed = CONTEXT_SIZE_TOKENS[task.context_size]
        if context_needed > model.context_window:
            context_fit = 0.0
        else:
            context_fit = min(1.0, model.context_window / context_needed)

        # 3. Speed match (15%)
        speed_score = SPEED_MATCH_SCORE.get(
            (task.speed_requirement, model.speed_category), 0.5
        )

        # 4. Cost efficiency (15%)
        avg_cost = (model.cost_per_1k_input + model.cost_per_1k_output) / 2
        cost_score = max(0.0, 1.0 - (avg_cost / MAX_COST_PER_TOKEN))

        # 5. Circuit breaker bonus (10%)
        cb_state = self.get_circuit_breaker_state(model.name)
        cb_bonus = 1.0 if cb_state == "closed" else 0.0

        score = (
            capability * 0.40
            + context_fit * 0.20
            + speed_score * 0.15
            + cost_score * 0.15
            + cb_bonus * 0.10
        )

        return round(score, 4)

    def _estimate_tokens(self, task: TaskProfile) -> int:
        """Estimate total tokens for a task."""
        token_estimates = {
            TaskType.CLASSIFICATION: 700,
            TaskType.CODE_GENERATION: 7000,
            TaskType.REVIEW: 7000,
            TaskType.PLANNING: 10000,
            TaskType.DECISION: 11500,
            TaskType.MONITORING: 1500,
        }
        base = token_estimates.get(task.task_type, 5000)
        # Scale by complexity
        return int(base * (0.5 + task.complexity * 0.1))

    def _estimate_cost(self, model: Model, task: TaskProfile) -> float:
        """Estimate cost in USD for a task."""
        total_tokens = self._estimate_tokens(task)
        input_ratio = 0.7  # 70% input, 30% output
        input_tokens = total_tokens * input_ratio
        output_tokens = total_tokens * (1 - input_ratio)

        cost = (
            input_tokens / 1000 * model.cost_per_1k_input
            + output_tokens / 1000 * model.cost_per_1k_output
        )
        return round(cost, 6)


class NoModelAvailableError(Exception):
    """Raised when no model is available for a task."""
    pass
