
from shared.config.model_router import ModelRouter


class TestModelRouter:
    def test_router_initialization(self):
        router = ModelRouter()
        assert router is not None

    def test_get_available_models(self):
        router = ModelRouter()
        models = router.get_available_models()
        assert len(models) >= 5

    def test_route_by_capability(self):
        router = ModelRouter()
        selected = router.route_task(
            task_type="code_generation",
            complexity="medium",
            context_size=4000,
        )
        assert selected is not None
        assert "model" in selected

    def test_route_with_budget_constraint(self):
        router = ModelRouter()
        selected = router.route_task(
            task_type="code_review",
            complexity="low",
            context_size=2000,
            max_cost_per_call=0.01,
        )
        assert selected is not None

    def test_circuit_breaker_excluded(self):
        router = ModelRouter()
        if hasattr(router, 'circuit_breaker'):
            router.circuit_breaker["test_model"] = {"state": "open"}
            models = router.get_available_models()
            model_names = [m.get("name") for m in models]
            assert "test_model" not in model_names
