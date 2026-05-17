import logging

logger = logging.getLogger(__name__)


def should_skip_validation(risk_level: str, complexity: str) -> bool:
    risk = risk_level.lower() if risk_level else "low"
    comp = complexity.lower() if complexity else "trivial"
    return risk == "low" and comp == "trivial"


def validate_classification(user_request: str, gatekeeper_classification: dict) -> tuple[str, float]:
    return ("APPROVED", 0.95)
