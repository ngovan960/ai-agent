"""Confidence Engine — AI SDLC Governance Layer (Phase 5.1)

Formula: Confidence = (T × 0.35) + (L × 0.15) - (P × 0.20) + (A × 0.30)
Clamped to [0, 1] per LAW-018.

Thresholds:
  >= 0.8  → auto_approve
  0.6-0.8 → require_review
  < 0.6   → escalate
  < 0.3   → takeover_rollback
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


WEIGHT_TEST = 0.35
WEIGHT_LINT = 0.15
WEIGHT_RETRY = 0.20
WEIGHT_LAW = 0.30

THRESHOLD_AUTO_APPROVE = 0.8
THRESHOLD_REQUIRE_REVIEW = 0.6
THRESHOLD_ESCALATE = 0.3


@dataclass
class ConfidenceBreakdown:
    test_pass_rate: float
    lint_score: float
    retry_penalty: float
    law_compliance: float


@dataclass
class ConfidenceResult:
    confidence_score: float
    breakdown: ConfidenceBreakdown
    action: str
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def calculate_test_pass_rate(test_results: dict[str, int]) -> float:
    """5.1.1 — T = passed / total (0-1)."""
    total = test_results.get("total", 0)
    if total == 0:
        return 0.0
    passed = test_results.get("passed", 0)
    return max(0.0, min(1.0, passed / total))


def calculate_lint_score(lint_results: dict[str, int]) -> float:
    """5.1.2 — L = 1 - (errors + warnings*0.5) / total_checks (0-1)."""
    total_checks = lint_results.get("total_checks", 0)
    if total_checks == 0:
        return 1.0
    errors = lint_results.get("errors", 0)
    warnings = lint_results.get("warnings", 0)
    score = 1.0 - (errors + warnings * 0.5) / total_checks
    return max(0.0, min(1.0, score))


def calculate_retry_penalty(retry_count: int, max_retries: int) -> float:
    """5.1.3 — P = retry_count / max_retries (0-1)."""
    if max_retries == 0:
        return 1.0
    return max(0.0, min(1.0, retry_count / max_retries))


def calculate_law_compliance(law_results: dict[str, int]) -> float:
    """5.1.4 — A = 1 - violated_laws / total_laws (0-1)."""
    total_laws = law_results.get("total_laws", 0)
    if total_laws == 0:
        return 1.0
    violated = law_results.get("violated_laws", 0)
    score = 1.0 - violated / total_laws
    return max(0.0, min(1.0, score))


def calculate_confidence(
    test_results: dict[str, int] | None = None,
    lint_results: dict[str, int] | None = None,
    retry_count: int = 0,
    max_retries: int = 2,
    law_results: dict[str, int] | None = None,
) -> ConfidenceResult:
    """5.1.5 — Full confidence calculation.

    Accepts raw inputs, computes T/L/P/A, applies formula, clamps to [0,1].
    """
    test_results = test_results or {}
    lint_results = lint_results or {}
    law_results = law_results or {}

    t_val = calculate_test_pass_rate(test_results)
    l_val = calculate_lint_score(lint_results)
    p_val = calculate_retry_penalty(retry_count, max_retries)
    a_val = calculate_law_compliance(law_results)

    raw = (t_val * WEIGHT_TEST) + (l_val * WEIGHT_LINT) - (p_val * WEIGHT_RETRY) + (a_val * WEIGHT_LAW)
    confidence = max(0.0, min(1.0, raw))

    return ConfidenceResult(
        confidence_score=round(confidence, 4),
        breakdown=ConfidenceBreakdown(
            test_pass_rate=round(t_val, 4),
            lint_score=round(l_val, 4),
            retry_penalty=round(p_val, 4),
            law_compliance=round(a_val, 4),
        ),
        action=decide_from_confidence(confidence),
    )


def decide_from_confidence(confidence: float) -> str:
    """5.1.6 — Threshold rules."""
    if confidence >= THRESHOLD_AUTO_APPROVE:
        return "auto_approve"
    if confidence >= THRESHOLD_REQUIRE_REVIEW:
        return "require_review"
    if confidence >= THRESHOLD_ESCALATE:
        return "escalate"
    return "takeover_rollback"


class ConfidenceEngine:
    """5.1 — Full confidence engine with history tracking and DB persistence."""

    def __init__(self, db_session=None):
        self._db = db_session
        self._history: list[dict[str, Any]] = []

    def calculate(
        self,
        task_id: UUID,
        test_results: dict[str, int] | None = None,
        lint_results: dict[str, int] | None = None,
        retry_count: int = 0,
        max_retries: int = 2,
        law_results: dict[str, int] | None = None,
    ) -> ConfidenceResult:
        """Calculate confidence for a task and log to history."""
        result = calculate_confidence(
            test_results=test_results,
            lint_results=lint_results,
            retry_count=retry_count,
            max_retries=max_retries,
            law_results=law_results,
        )
        self._log_confidence(task_id, result)
        return result

    def _log_confidence(self, task_id: UUID, result: ConfidenceResult) -> dict[str, Any]:
        """5.1.8 — Log confidence to history."""
        entry = {
            "task_id": str(task_id),
            "confidence_score": result.confidence_score,
            "test_pass_rate": result.breakdown.test_pass_rate,
            "lint_score": result.breakdown.lint_score,
            "retry_penalty": result.breakdown.retry_penalty,
            "law_compliance": result.breakdown.law_compliance,
            "action": result.action,
            "calculated_at": result.calculated_at.isoformat(),
        }
        self._history.append(entry)
        logger.info(
            f"Confidence for {task_id}: {result.confidence_score:.4f} "
            f"(T={result.breakdown.test_pass_rate}, L={result.breakdown.lint_score}, "
            f"P={result.breakdown.retry_penalty}, A={result.breakdown.law_compliance}) "
            f"→ {result.action}"
        )
        return entry

    def get_history(self, task_id: UUID) -> list[dict[str, Any]]:
        """Get confidence history for a task."""
        return [h for h in self._history if h["task_id"] == str(task_id)]

    def get_all_history(self) -> list[dict[str, Any]]:
        """Get all confidence history."""
        return list(self._history)
