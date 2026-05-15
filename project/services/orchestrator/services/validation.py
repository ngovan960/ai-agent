import json
import logging
import re
import uuid
from datetime import datetime, timezone

from shared.schemas.validation import (
    ValidationRequest,
    ValidationResponse,
    GatekeeperClassification,
    ValidatorVerdict,
    ValidationVerdict,
    RiskLevel,
    Complexity,
    TaskType,
)

logger = logging.getLogger(__name__)

VALIDATION_THRESHOLD = 0.8
REANALYZE_THRESHOLD = 0.5
MAX_USER_REQUEST_LENGTH = 5000


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


def _sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent prompt injection."""
    if not text:
        return ""
    text = text[:MAX_USER_REQUEST_LENGTH]
    text = text.replace("<|", "< |")
    text = text.replace("|>", "| >")
    text = text.replace("{{", "{ {")
    text = text.replace("}}", "} }")
    text = text.replace("ignore all previous instructions", "[REDACTED]")
    text = text.replace("ignore previous instructions", "[REDACTED]")
    text = text.replace("disregard all previous", "[REDACTED]")
    text = re.sub(r"(system|user|assistant)\s*:\s*", r"[ROLE:\1] ", text, flags=re.IGNORECASE)
    return text


def _build_validator_prompt(request: ValidationRequest) -> str:
    gk = request.gatekeeper_classification
    sanitized_request = _sanitize_user_input(request.user_request)
    return (
        "### SYSTEM: Validation Agent\n"
        "You are a Validation Agent responsible for reviewing the Gatekeeper's classification.\n"
        "You MUST respond with ONLY a valid JSON object. No other text.\n\n"
        "### TASK\n"
        "Review the Gatekeeper's classification of the user request below.\n"
        "Check: task_type accuracy, complexity reasonableness, risk level appropriateness, effort estimate realism.\n\n"
        "### USER REQUEST (sanitized)\n"
        f"<request>\n{sanitized_request}\n</request>\n\n"
        "### GATEKEEPER CLASSIFICATION\n"
        f"- Task Type: {gk.task_type.value}\n"
        f"- Complexity: {gk.complexity.value}\n"
        f"- Risk Level: {gk.risk_level.value}\n"
        f"- Estimated Effort: {gk.estimated_effort}\n"
        f"- Confidence: {gk.confidence}\n"
        f"- Reasoning: {gk.reasoning}\n\n"
        "### RESPONSE FORMAT\n"
        '{"verdict": "APPROVED|REJECTED|NEEDS_REVIEW", "confidence": 0.0-1.0, "reason": "explanation"}'
    )


def _parse_validator_response(response_text: str) -> ValidatorVerdict:
    """Parse the LLM validator response into a ValidatorVerdict."""
    try:
        json_match = re.search(r'\{[^{}]*"verdict"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            verdict_str = str(data.get("verdict", "NEEDS_REVIEW")).upper()
            if "APPROVED" in verdict_str:
                verdict = ValidationVerdict.APPROVED
            elif "REJECTED" in verdict_str:
                verdict = ValidationVerdict.REJECTED
            else:
                verdict = ValidationVerdict.NEEDS_REVIEW
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            reason = str(data.get("reason", "No reason provided"))
            return ValidatorVerdict(
                verdict=verdict,
                confidence=confidence,
                reason=reason,
            )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning(f"Failed to parse validator response: {e}")

    return ValidatorVerdict(
        verdict=ValidationVerdict.NEEDS_REVIEW,
        confidence=0.5,
        reason="Could not parse validator response — manual review recommended",
    )


async def _call_validator_llm(request: ValidationRequest) -> ValidatorVerdict:
    """Call the Validator LLM to cross-validate the Gatekeeper's classification."""
    prompt = _build_validator_prompt(request)

    try:
        from litellm import acompletion

        response = await acompletion(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1,
        )
        response_text = response.choices[0].message.content
        logger.info(f"Validator LLM response: {response_text[:200]}")
        return _parse_validator_response(response_text)

    except Exception as e:
        logger.warning(f"Validator LLM call failed, falling back to threshold-based: {e}")
        return _threshold_fallback(request.gatekeeper_classification)


def _threshold_fallback(gk: GatekeeperClassification) -> ValidatorVerdict:
    """Fallback validator using confidence thresholds when LLM is unavailable."""
    if gk.confidence >= VALIDATION_THRESHOLD:
        return ValidatorVerdict(
            verdict=ValidationVerdict.APPROVED,
            confidence=gk.confidence,
            reason="Threshold-based approval (LLM validator unavailable)",
        )
    elif gk.confidence >= REANALYZE_THRESHOLD:
        return ValidatorVerdict(
            verdict=ValidationVerdict.NEEDS_REVIEW,
            confidence=gk.confidence,
            reason="Threshold-based review (LLM validator unavailable)",
        )
    else:
        return ValidatorVerdict(
            verdict=ValidationVerdict.REJECTED,
            confidence=gk.confidence,
            reason="Threshold-based rejection — confidence too low, escalate to Mentor",
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
    """
    Validate the Gatekeeper's classification.
    
    Uses threshold-based validation inline (synchronous).
    For LLM-based validation, use validate_classification_async().
    """
    gk = request.gatekeeper_classification

    risk_config = RISK_VALIDATION_MATRIX.get(
        gk.risk_level, {"require_validator": True, "require_mentor": False}
    )
    complexity_config = COMPLEXITY_VALIDATION_MATRIX.get(
        gk.complexity, {"require_validator": True}
    )

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
        validator_verdict = _threshold_fallback(gk)
        verdict = validator_verdict.verdict
        confidence = validator_verdict.confidence
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


async def validate_classification_async(request: ValidationRequest) -> ValidationResponse:
    """
    Validate the Gatekeeper's classification using the LLM Validator.
    
    Calls the Validator LLM for cross-validation, with fallback to thresholds
    if LLM is unavailable.
    """
    gk = request.gatekeeper_classification

    risk_config = RISK_VALIDATION_MATRIX.get(
        gk.risk_level, {"require_validator": True, "require_mentor": False}
    )
    complexity_config = COMPLEXITY_VALIDATION_MATRIX.get(
        gk.complexity, {"require_validator": True}
    )

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
        validator_verdict = await _call_validator_llm(request)
        verdict = validator_verdict.verdict
        confidence = validator_verdict.confidence
        final_classification = (
            validator_verdict.suggested_classification
            or gk
        )

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
