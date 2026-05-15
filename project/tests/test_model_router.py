import pytest
from uuid import uuid4

from shared.config.model_router import ModelRouter, Model, SpeedCategory, TaskType, ContextSize
from shared.config.settings import get_settings


def _default_models():
    return [
        Model(
            name="deepseek-v4-flash", provider="deepseek",
            context_window=128000, max_output_tokens=8000,
            cost_per_1k_input=0.0001, cost_per_1k_output=0.0002,
            timeout_seconds=60, speed_category=SpeedCategory.FAST,
            capabilities={"code": True}, strengths=["fast"], weaknesses=[],
            best_for=["quick_tasks"], avoid_for=["complex_reasoning"],
        ),
        Model(
            name="deepseek-v4-pro", provider="deepseek",
            context_window=128000, max_output_tokens=8000,
            cost_per_1k_input=0.0005, cost_per_1k_output=0.001,
            timeout_seconds=120, speed_category=SpeedCategory.MEDIUM,
            capabilities={"code": True, "reasoning": True}, strengths=["accurate"], weaknesses=[],
            best_for=["complex_tasks"], avoid_for=[],
        ),
        Model(
            name="qwen-3.5-plus", provider="qwen",
            context_window=32000, max_output_tokens=4000,
            cost_per_1k_input=0.0002, cost_per_1k_output=0.0004,
            timeout_seconds=60, speed_category=SpeedCategory.FAST,
            capabilities={"code": True}, strengths=["balanced"], weaknesses=[],
            best_for=["general_tasks"], avoid_for=[],
        ),
        Model(
            name="qwen-3.6-plus", provider="qwen",
            context_window=32000, max_output_tokens=4000,
            cost_per_1k_input=0.0003, cost_per_1k_output=0.0006,
            timeout_seconds=90, speed_category=SpeedCategory.MEDIUM,
            capabilities={"code": True, "reasoning": True}, strengths=["versatile"], weaknesses=[],
            best_for=["review_tasks"], avoid_for=[],
        ),
        Model(
            name="minimax-m2.7", provider="minimax",
            context_window=32000, max_output_tokens=4000,
            cost_per_1k_input=0.0004, cost_per_1k_output=0.0008,
            timeout_seconds=90, speed_category=SpeedCategory.MEDIUM,
            capabilities={"code": True}, strengths=["creative"], weaknesses=[],
            best_for=["creative_tasks"], avoid_for=[],
        ),
    ]


class TestModelRouter:
    def test_router_initialization(self):
        router = ModelRouter(models=_default_models())
        assert router is not None

    def test_get_available_models(self):
        router = ModelRouter(models=_default_models())
        models = router.models
        assert len(models) >= 5

    def test_route_by_capability(self):
        router = ModelRouter(models=_default_models())
        from shared.config.model_router import TaskProfile
        selected = router.select(TaskProfile(
            task_type=TaskType.CODE_GENERATION,
            complexity=5,
            context_size=ContextSize.MEDIUM,
        ))
        assert selected is not None
        assert selected.primary is not None

    def test_route_with_budget_constraint(self):
        router = ModelRouter(models=_default_models())
        from shared.config.model_router import TaskProfile
        selected = router.select(TaskProfile(
            task_type=TaskType.REVIEW,
            complexity=3,
            context_size=ContextSize.SMALL,
            budget_usd=0.01,
        ))
        assert selected is not None

    def test_circuit_breaker_excluded(self):
        router = ModelRouter(models=_default_models())
        router.set_circuit_breaker_state("deepseek-v4-flash", "open")
        from shared.config.model_router import TaskProfile
        selected = router.select(TaskProfile(
            task_type=TaskType.CODE_GENERATION,
            complexity=5,
            context_size=ContextSize.MEDIUM,
        ))
        assert selected.primary.name != "deepseek-v4-flash"
