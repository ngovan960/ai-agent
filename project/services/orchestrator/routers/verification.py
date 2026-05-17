import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services import tasks as task_service
from services.orchestrator.services.confidence_engine import ConfidenceEngine
from services.orchestrator.services.mode_selector import ModeSelector
from services.orchestrator.services.rollback_service import RollbackEngine
from services.orchestrator.services.verification_service import VerificationPipeline
from shared.database import get_db
from shared.schemas.verification import (
    RollbackRequest,
    RollbackResponse,
    VerificationRequest,
    VerificationResponse,
    VerificationStatusResponse,
)
from shared.schemas.verification import (
    StepResult as StepResultSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tasks", tags=["verification"])

_verification_cache: dict[str, dict] = {}
_confidence_engine = ConfidenceEngine()


@router.post("/{task_id}/verify", response_model=VerificationResponse)
async def verify_task(
    task_id: UUID,
    request: VerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    mode_selector = ModeSelector()
    mode = request.mode or mode_selector.select(
        task.risk_level.value if hasattr(task.risk_level, "value") else str(task.risk_level)
    )

    pipeline = VerificationPipeline()
    code_path = request.code_path or f"/tmp/workspace/{task_id.hex[:12]}"

    result = await pipeline.run_pipeline(
        task_id=task_id,
        code_path=code_path,
        mode=mode,
    )

    trust = _confidence_engine.calculate(
        task_id=task_id,
        test_results={"passed": sum(1 for s in result.steps if s.status == "verified"), "total": len(result.steps)},
        lint_results={"errors": sum(len(s.errors) for s in result.steps), "warnings": 0, "total_checks": len(result.steps)},
        retry_count=task.retries or 0,
        max_retries=task.max_retries or 2,
        law_results={"total_laws": 20, "violated_laws": len(result.errors)},
    )

    logger.info(
        f"Confidence for {task_id}: {trust.confidence_score:.4f} → {trust.action} "
        f"(verification score: {result.score})"
    )

    cache_key = str(task_id)
    _verification_cache[cache_key] = {
        "status": result.status,
        "score": result.score,
        "mode": result.mode,
        "steps": [
            {
                "step_name": s.step_name,
                "status": s.status,
                "exit_code": s.exit_code,
                "stdout": s.stdout[:1000],
                "stderr": s.stderr[:1000],
                "duration_ms": s.duration_ms,
                "errors": s.errors,
            }
            for s in result.steps
        ],
        "errors": result.errors,
        "logs": result.logs,
        "duration_ms": result.duration_ms,
    }

    status = result.status
    if status == "verified":
        from shared.schemas.task import StateTransitionRequest
        next_state = "REVIEWING"
        if trust.action == "auto_approve":
            next_state = "DONE"
        elif trust.action == "escalate" or trust.action == "takeover_rollback":
            next_state = "ESCALATED"

        await task_service.transition_task_state(
            db, task_id,
            StateTransitionRequest(
                target_status=next_state,
                reason=f"Verification passed (score={result.score}, confidence={trust.confidence_score:.4f}, action={trust.action})",
            ),
        )
    else:
        from shared.schemas.task import StateTransitionRequest
        await task_service.transition_task_state(
            db, task_id,
            StateTransitionRequest(
                target_status="IMPLEMENTING",
                reason=f"Verification failed (score={result.score}, confidence={trust.confidence_score:.4f})",
            ),
        )

    task.confidence = trust.confidence_score
    await db.flush()

    return VerificationResponse(
        task_id=task_id,
        status=status,
        score=result.score,
        steps=[StepResultSchema(**s.__dict__) for s in result.steps],
        errors=result.errors,
        duration_ms=result.duration_ms,
        mode=result.mode,
    )


@router.get("/{task_id}/verification-result", response_model=VerificationStatusResponse)
async def get_verification_result(task_id: UUID):
    cache_key = str(task_id)
    cached = _verification_cache.get(cache_key)
    if not cached:
        raise HTTPException(status_code=404, detail="No verification result found")
    return VerificationStatusResponse(
        task_id=task_id,
        status=cached["status"],
        score=cached["score"],
        mode=cached["mode"],
    )


@router.post("/{task_id}/rollback", response_model=RollbackResponse)
async def rollback_task(
    task_id: UUID,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    engine = RollbackEngine()
    record = await engine.trigger_rollback(
        task_id=task_id,
        reason=request.reason,
    )

    if record.status == "failed":
        raise HTTPException(status_code=500, detail=record.result)

    return RollbackResponse(
        task_id=task_id,
        status=record.status,
        reason=request.reason,
        rollback_id=record.rollback_id,
        message=f"Rollback {record.status}: {record.result[:200]}",
    )
