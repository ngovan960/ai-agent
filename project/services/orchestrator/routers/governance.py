"""Governance API routers — Phase 5: Confidence, Laws, Cost, Risk."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services.confidence_engine import ConfidenceEngine
from services.orchestrator.services.cost_governor import CostGovernor
from services.orchestrator.services.law_engine import LawEngine
from services.orchestrator.services.risk_classifier import RiskClassifier
from shared.database import get_db
from shared.schemas.confidence import ConfidenceBreakdown as ConfidenceBreakdownSchema
from shared.schemas.confidence import ConfidenceHistoryResponse, ConfidenceResponse
from shared.schemas.cost import CostStatsResponse
from shared.schemas.law import Law, LawListResponse, ViolationReport
from shared.schemas.risk import RiskResponse

router = APIRouter()

_confidence_engine = ConfidenceEngine()
_law_engine = LawEngine()
_risk_classifier = RiskClassifier()


@router.get("/tasks/{task_id}/confidence", response_model=ConfidenceResponse)
async def get_task_confidence(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    test_passed: int = Query(0),
    test_total: int = Query(0),
    lint_errors: int = Query(0),
    lint_warnings: int = Query(0),
    lint_checks: int = Query(0),
    retry_count: int = Query(0),
    max_retries: int = Query(2),
    law_total: int = Query(0),
    law_violated: int = Query(0),
):
    """5.1.7 — GET /api/v1/tasks/{task_id}/confidence"""

    test_results = {"passed": test_passed, "total": test_total} if test_total > 0 else {}
    lint_results = {"errors": lint_errors, "warnings": lint_warnings, "total_checks": lint_checks} if lint_checks > 0 else {}
    law_results = {"total_laws": law_total, "violated_laws": law_violated} if law_total > 0 else {}

    result = _confidence_engine.calculate(
        task_id=task_id,
        test_results=test_results,
        lint_results=lint_results,
        retry_count=retry_count,
        max_retries=max_retries,
        law_results=law_results,
    )

    return ConfidenceResponse(
        task_id=task_id,
        confidence_score=result.confidence_score,
        breakdown=ConfidenceBreakdownSchema(
            test_pass_rate=result.breakdown.test_pass_rate,
            lint_score=result.breakdown.lint_score,
            retry_penalty=result.breakdown.retry_penalty,
            law_compliance=result.breakdown.law_compliance,
        ),
        action=result.action,
        calculated_at=result.calculated_at,
    )


@router.get("/tasks/{task_id}/confidence/history", response_model=ConfidenceHistoryResponse)
async def get_task_confidence_history(task_id: UUID):
    """Get confidence history for a task."""
    history = _confidence_engine.get_history(task_id)
    return ConfidenceHistoryResponse(
        task_id=task_id,
        total_entries=len(history),
        history=history,
    )


@router.get("/laws", response_model=LawListResponse)
async def list_laws():
    """5.2.6 — GET /api/v1/laws"""
    laws = _law_engine.get_laws()
    return LawListResponse(laws=laws, total=len(laws))


@router.post("/laws", response_model=Law, status_code=201)
async def create_law(law: Law):
    """5.2.7 — POST /api/v1/laws (add custom law in-memory)"""
    return _law_engine.add_law(law)


@router.get("/tasks/{task_id}/law-violations", response_model=ViolationReport)
async def get_task_law_violations(
    task_id: UUID,
    code: str = Query("", description="Code content to check"),
    filename: str = Query("", description="Filename for context"),
):
    """5.2.8 — GET /api/v1/tasks/{task_id}/law-violations"""
    if not code:
        raise HTTPException(status_code=400, detail="code query parameter is required")
    report = _law_engine.check_compliance(code=code, filename=filename or None, task_id=task_id)
    return _law_engine.report_violations(report)


@router.get("/cost-stats", response_model=CostStatsResponse)
async def get_cost_stats(
    db: AsyncSession = Depends(get_db),
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
):
    """5.3.7 — GET /api/v1/cost-stats"""
    governor = CostGovernor(db_session=db)
    return await governor.get_cost_stats(period=period)


@router.get("/cost-stats/{project_id}", response_model=CostStatsResponse)
async def get_project_cost_stats(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
):
    """5.3.8 — GET /api/v1/cost-stats/{project_id}"""
    governor = CostGovernor(db_session=db)
    return await governor.get_cost_stats(project_id=project_id, period=period)


@router.get("/tasks/{task_id}/risk", response_model=RiskResponse)
async def get_task_risk(
    task_id: UUID,
    complexity: int = Query(5, ge=1, le=10),
    data_sensitivity: int = Query(0, ge=0, le=3),
    user_impact: int = Query(0, ge=0, le=3),
    deployment_scope: int = Query(0, ge=0, le=2),
):
    """5.4.5 — GET /api/v1/tasks/{task_id}/risk"""
    classification = _risk_classifier.classify(
        task_id=task_id,
        complexity=complexity,
        data_sensitivity=data_sensitivity,
        user_impact=user_impact,
        deployment_scope=deployment_scope,
    )
    return _risk_classifier.to_response(task_id, classification)
