"""Risk Classification — AI SDLC Governance Layer (Phase 5.4)

Classifies task risk based on complexity, data sensitivity, user impact,
and deployment scope. Maps risk levels to appropriate actions and workflow paths.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from shared.schemas.risk import RiskFactors, RiskResponse

logger = logging.getLogger(__name__)

RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_CRITICAL = "CRITICAL"

ACTION_AUTO_APPROVE = "auto_approve"
ACTION_REQUIRE_AUDIT = "require_audit"
ACTION_SENIOR_REVIEW = "senior_review_and_audit"
ACTION_HUMAN_APPROVAL = "human_approval"

PATH_FAST_TRACK = "fast_track"
PATH_STANDARD = "standard"
PATH_REVIEW_GATE = "review_gate"
PATH_FULL_REVIEW = "full_review_human_approval"


@dataclass
class RiskClassification:
    risk_score: float
    risk_level: str
    factors: RiskFactors
    recommended_action: str
    workflow_path: str


def calculate_risk_score(
    complexity: int = 5,
    data_sensitivity: int = 0,
    user_impact: int = 0,
    deployment_scope: int = 0,
) -> float:
    """5.4.1 — Calculate risk score (1-10).

    Formula: score = (complexity * 0.5) + (data_sensitivity * 1.0) + (user_impact * 1.0) + (deployment_scope * 1.25)
    Clamped to [1, 10].
    """
    raw = (complexity * 0.5) + (data_sensitivity * 1.0) + (user_impact * 1.0) + (deployment_scope * 1.25)
    return max(1.0, min(10.0, round(raw, 2)))


def classify_risk(score: float) -> str:
    """5.4.2 — Map score to risk level."""
    if score <= 3:
        return RISK_LEVEL_LOW
    if score <= 6:
        return RISK_LEVEL_MEDIUM
    if score <= 8:
        return RISK_LEVEL_HIGH
    return RISK_LEVEL_CRITICAL


def get_risk_action(risk_level: str) -> str:
    """5.4.3 — Map risk level to required action."""
    actions = {
        RISK_LEVEL_LOW: ACTION_AUTO_APPROVE,
        RISK_LEVEL_MEDIUM: ACTION_REQUIRE_AUDIT,
        RISK_LEVEL_HIGH: ACTION_SENIOR_REVIEW,
        RISK_LEVEL_CRITICAL: ACTION_HUMAN_APPROVAL,
    }
    return actions.get(risk_level, ACTION_REQUIRE_AUDIT)


def route_by_risk(risk_level: str) -> str:
    """5.4.6 — Map risk level to workflow path."""
    paths = {
        RISK_LEVEL_LOW: PATH_FAST_TRACK,
        RISK_LEVEL_MEDIUM: PATH_STANDARD,
        RISK_LEVEL_HIGH: PATH_REVIEW_GATE,
        RISK_LEVEL_CRITICAL: PATH_FULL_REVIEW,
    }
    return paths.get(risk_level, PATH_STANDARD)


class RiskClassifier:
    """5.4 — Risk classification for tasks."""

    def classify(
        self,
        task_id: UUID,
        complexity: int = 5,
        data_sensitivity: int = 0,
        user_impact: int = 0,
        deployment_scope: int = 0,
    ) -> RiskClassification:
        """Classify task risk and return full classification."""
        factors = RiskFactors(
            complexity=complexity,
            data_sensitivity=data_sensitivity,
            user_impact=user_impact,
            deployment_scope=deployment_scope,
        )

        score = calculate_risk_score(
            complexity=complexity,
            data_sensitivity=data_sensitivity,
            user_impact=user_impact,
            deployment_scope=deployment_scope,
        )

        risk_level = classify_risk(score)
        action = get_risk_action(risk_level)
        workflow_path = route_by_risk(risk_level)

        logger.info(
            f"Risk for {task_id}: score={score}, level={risk_level}, "
            f"action={action}, path={workflow_path}"
        )

        return RiskClassification(
            risk_score=score,
            risk_level=risk_level,
            factors=factors,
            recommended_action=action,
            workflow_path=workflow_path,
        )

    async def update_task_risk(
        self,
        task_id: UUID,
        db_session,
        complexity: int = 5,
        data_sensitivity: int = 0,
        user_impact: int = 0,
        deployment_scope: int = 0,
    ) -> RiskClassification:
        """5.4.4 — Calculate and persist risk to the task."""
        from sqlalchemy import select

        from shared.models.task import RiskLevel, Task

        classification = self.classify(
            task_id=task_id,
            complexity=complexity,
            data_sensitivity=data_sensitivity,
            user_impact=user_impact,
            deployment_scope=deployment_scope,
        )

        stmt = select(Task).where(Task.id == task_id)
        result = await db_session.execute(stmt)
        task = result.scalar_one_or_none()
        if task:
            task.risk_score = classification.risk_score
            task.risk_level = RiskLevel(classification.risk_level)
            await db_session.flush()

        return classification

    def to_response(self, task_id: UUID, classification: RiskClassification) -> RiskResponse:
        """Convert classification to API response."""
        return RiskResponse(
            task_id=task_id,
            risk_score=classification.risk_score,
            risk_level=classification.risk_level,
            factors=classification.factors,
            recommended_action=classification.recommended_action,
            workflow_path=classification.workflow_path,
        )
