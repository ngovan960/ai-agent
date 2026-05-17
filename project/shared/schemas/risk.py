from uuid import UUID

from pydantic import BaseModel, Field


class RiskFactors(BaseModel):
    complexity: int = Field(ge=1, le=10, description="Task complexity (1-10)")
    data_sensitivity: int = Field(ge=0, le=3, description="Data sensitivity (0-3)")
    user_impact: int = Field(ge=0, le=3, description="User impact (0-3)")
    deployment_scope: int = Field(ge=0, le=2, description="Deployment scope (0-2)")


class RiskResponse(BaseModel):
    task_id: UUID
    risk_score: float = Field(ge=1, le=10)
    risk_level: str
    factors: RiskFactors
    recommended_action: str
    workflow_path: str
