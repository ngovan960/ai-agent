import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class ExecutionMode(StrEnum):
    DEV = "dev"
    PROD = "prod"


RISK_MODE_MAP = {
    "LOW": ExecutionMode.DEV,
    "MEDIUM": ExecutionMode.DEV,
    "HIGH": ExecutionMode.PROD,
    "CRITICAL": ExecutionMode.PROD,
}


def select_mode(risk_level: str) -> ExecutionMode:
    return RISK_MODE_MAP.get(risk_level.upper(), ExecutionMode.DEV)


def should_use_prod(risk_level: str) -> bool:
    return select_mode(risk_level) == ExecutionMode.PROD


class ModeSelector:
    def select(self, risk_level: str) -> str:
        return select_mode(risk_level).value

    def requires_sandbox(self, risk_level: str) -> bool:
        return should_use_prod(risk_level)


MAX_VERIFICATION_RETRIES = 2


def handle_verification_fail(result: dict, retry_count: int = 0) -> str:
    status = result.get("status", "failed")
    score = result.get("score", 0)  # noqa: F841
    if status == "verified":
        return "proceed"
    if retry_count < MAX_VERIFICATION_RETRIES:
        return "retry"
    return "escalate"
