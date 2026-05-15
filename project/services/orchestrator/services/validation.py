import uuid
import json
import logging
from datetime import datetime, timezone

from shared.schemas.validation import (
    ValidationRequest,
    ValidationResponse,
    GatekeeperClassification,
    ValidatorVerdict,
    ValidationVerdict,
    RiskLevel,
    Complexity,
)

logger = logging.getLogger(__name__)

VALIDATION_THRESHOLD = 0.8
REANALYZE_THRESHOLD = 0.5

RISK_VALIDATION_MATRIX = {
    RiskLevel.LOW: {"require_validator": False, "require_mentor": False},
    RiskLevel.MEDIUM: {"require_validator": True, "require_mentor": False},
    RiskLevel.HIGH: {"require_validator": True, "require_mentor": True},
    RiskLevel.CRITICAL: {"require_validator": True, "require_mentor": True},
}

COMPLEXITY_VALIDATION_MATRIX = {
    Complexity.TRIVIAL: {"require_validator": False},
    Complexity.SIMPLE: {"require_validator": False},
    Complexity.MEDIUM: {"require_validator": True},
    Complexity.COMPLEX: {"require_validator": True},
    Complexity.CRITICAL: {"require_validator": True},
}


def _build_validator_prompt(request: ValidationRequest) -> str:
    gk = request.gatekeeper_classification
    return (
        f"You are a Validation Agent. Review the Gatekeeper's classification of a user request.\n\n"
        f"USER REQUEST: {request.user_request}\n\n"
        f"GATEKEEPER CLASSIFICATION:\n"
        f"- Task Type: {gk.task_type.value}\n"
        f"- Complexity: {gk.complexity.value}\n"
        f"- Risk Level: {gk.risk_level.value}\n"
        f"- Estimated Effort: {gk.estimated_effort}\n"
        f"- Confidence: {gk.confidence}\n"
        f"- Reasoning: {gk.reasoning}\n\n"
        f"TASKS:\n"
        f"1. Is the task_type correct? If not, what should it be?\n"
        f"2. Is the complexity assessment accurate? Over-estimated or under-estimated?\n"
        f"3. Is the risk level appropriate?\n"
        f"4. Is the estimated effort realistic?\n"
        f"5. Does the reasoning make sense?\n\n"
        f"Respond with: APPROVED if classification is correct, REJECTED if wrong, NEEDS_REVIEW if uncertain.\n"
        f"Provide specific mismatch details and your suggested classification if different."
    )


def _determine_action(
    verdict: ValidationVerdict,
    confidence: float,
    risk_level: RiskLevel,
    complexity: Complexity,
) -> str:
    if verdict == ValidationVerdict.REJECTED:
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return "escalate_to_mentor"
        return "reanalyze"

    if verdict == ValidationVerdict.NEEDS_REVIEW:
        if confidence < REANALYZE_THRESHOLD:
            return "escalate_to_mentor"
        return "reanalyze"

    if confidence >= VALIDATION_THRESHOLD:
        return "pass_to_orchestrator"

    return "reanalyze"


def validate_classification(request: ValidationRequest) -> ValidationResponse:
    gk = request.gatekeeper_classification

    risk_config = RISK_VALIDATION_MATRIX.get(gk.risk_level, {"require_validator": True, "require_mentor": False})
    complexity_config = COMPLEXITY_VALIDATION_MATRIX.get(gk.complexity, {"require_validator": True})

    requires_validator = risk_config["require_validator"] or complexity_config["require_validator"]

    if not requires_validator:
        final_classification = gk
        verdict = ValidationVerdict.APPROVED
        confidence = gk.confidence
        validator_verdict = ValidatorVerdict(
            verdict=ValidationVerdict.APPROVED,
            confidence=1.0,
            reason="Low risk, trivial/simple task — validator skipped",
        )
    else:
        verdict = ValidationVerdict.APPROVED
        confidence = gk.confidence

        if gk.confidence < 0.5:
            verdict = ValidationVerdict.NEEDS_REVIEW
            confidence = gk.confidence
        elif gk.confidence < VALIDATION_THRESHOLD:
            verdict = ValidationVerdict.NEEDS_REVIEW
            confidence = gk.confidence

        validator_verdict = ValidatorVerdict(
            verdict=verdict,
            confidence=confidence,
            reason="Validator review based on confidence threshold and risk level",
        )

        final_classification = gk

    action = _determine_action(verdict, confidence, gk.risk_level, gk.complexity)

    return ValidationResponse(
        id=uuid.uuid4(),
        request_id=request.task_id,
        task_id=request.task_id,
        verdict=verdict,
        confidence=confidence,
        gatekeeper_classification=gk,
        validator_verdict=validator_verdict,
        final_classification=final_classification,
        action=action,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def should_skip_validation(risk_level: RiskLevel, complexity: Complexity) -> bool:
    risk_config = RISK_VALIDATION_MATRIX.get(risk_level, {"require_validator": True})
    complexity_config = COMPLEXITY_VALIDATION_MATRIX.get(complexity, {"require_validator": True})
    return not risk_config["require_validator"] and not complexity_config["require_validator"]
