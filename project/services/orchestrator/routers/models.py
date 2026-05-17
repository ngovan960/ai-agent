import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ModelSelectRequest(BaseModel):
    agent_name: str
    task_spec: str | None = None
    complexity: str | None = "medium"
    risk_level: str | None = "medium"


class ModelSelectResponse(BaseModel):
    model: str
    fallbacks: list[str] = []
    llm_path: str
    estimated_cost: float = 0.0
    score: float = 0.0


@router.post("/select", response_model=ModelSelectResponse)
async def select_model(req: ModelSelectRequest, db: AsyncSession = Depends(get_db)):
    from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
    from shared.config.model_router import ModelRouter

    try:

        router = ModelRouter(  # type: ignore
            models=_load_models()
        )

        builder = TaskProfileBuilder(router)
        profile = builder.build(
            agent_name=req.agent_name,
            complexity=req.complexity,
            risk_level=req.risk_level,
        )
        selection = router.select(profile)

        return ModelSelectResponse(
            model=selection.primary.name,
            fallbacks=[m.name for m in selection.fallbacks],
            llm_path=selection.llm_path.value,
            estimated_cost=selection.estimated_cost,
            score=1.0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _load_models():
    from pathlib import Path

    import yaml

    from shared.config.model_router import Model

    config_path = None
    # Walk up from this file to find the project root containing 'shared/config'
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "shared" / "config" / "model_capabilities.yaml"
        if candidate.exists():
            config_path = candidate
            break
        if current.parent == current:
            break
        current = current.parent

    if config_path is None:
        config_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "shared" / "config" / "model_capabilities.yaml"
        )
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception:
        config = {}

    models_data = config.get("models", {})
    models = []
    for name, data in models_data.items():
        caps = data.get("capabilities", {})
        models.append(
            Model(
                name=name,
                provider=data.get("provider", "unknown"),
                context_window=data.get("context_window", 4096),
                max_output_tokens=data.get("max_output_tokens", 4096),
                cost_per_1k_input=data.get("cost_per_1k_input_tokens", 0.001),
                cost_per_1k_output=data.get("cost_per_1k_output_tokens", 0.002),
                timeout_seconds=data.get("timeout_seconds", 30),
                speed_category=data.get("speed_category", "medium"),
                capabilities=caps,
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                best_for=data.get("best_for", []),
                avoid_for=data.get("avoid_for", []),
            )
        )
    return models
