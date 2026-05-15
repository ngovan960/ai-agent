from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas.validation import (
    ValidationRequest,
    ValidationResponse,
    ValidationHistoryResponse,
    GatekeeperClassification,
    TaskType,
    Complexity,
    RiskLevel,
)
from services.orchestrator.services import validation as validation_service

router = APIRouter()


@router.post("/", response_model=ValidationResponse, status_code=201)
async def validate_classification(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await validation_service.validate_classification_async(request)
    return result


@router.post("/quick", response_model=ValidationResponse, status_code=201)
async def quick_validate(
    user_request: str,
    task_type: TaskType,
    complexity: Complexity,
    risk_level: RiskLevel,
    estimated_effort: str = "1d",
    confidence: float = 0.7,
    reasoning: str = "",
    db: AsyncSession = Depends(get_db),
):
    classification = GatekeeperClassification(
        task_type=task_type,
        complexity=complexity,
        risk_level=risk_level,
        estimated_effort=estimated_effort,
        confidence=confidence,
        reasoning=reasoning,
    )
    request = ValidationRequest(
        user_request=user_request,
        gatekeeper_classification=classification,
    )
    result = await validation_service.validate_classification_async(request)
    return result


@router.get("/should-skip")
async def check_skip_validation(
    risk_level: RiskLevel = RiskLevel.LOW,
    complexity: Complexity = Complexity.SIMPLE,
):
    skip = validation_service.should_skip_validation(risk_level, complexity)
    return {"skip_validation": skip, "risk_level": risk_level.value, "complexity": complexity.value}
