import logging

from shared.config.model_router import (
    ContextSize,
    ModelRouter,
    SpeedRequirement,
    TaskProfile,
    TaskType,
)
from shared.models.task import Task

logger = logging.getLogger(__name__)

AGENT_TO_TASK_TYPE: dict[str, TaskType] = {
    "gatekeeper": TaskType.CLASSIFICATION,
    "validator": TaskType.CLASSIFICATION,
    "orchestrator": TaskType.PLANNING,
    "specialist": TaskType.CODE_GENERATION,
    "auditor": TaskType.REVIEW,
    "mentor": TaskType.DECISION,
    "devops": TaskType.CODE_GENERATION,
    "monitoring": TaskType.MONITORING,
}

AGENT_TO_STATE: dict[str, str] = {
    "gatekeeper": "NEW",
    "validator": "VALIDATING",
    "orchestrator": "ANALYZING",
    "specialist": "IMPLEMENTING",
    "auditor": "REVIEWING",
    "mentor": "ESCALATED",
    "devops": "IMPLEMENTING",
    "monitoring": "ANALYZING",
}

AGENT_TO_SPEED: dict[str, SpeedRequirement] = {
    "gatekeeper": SpeedRequirement.FAST,
    "validator": SpeedRequirement.BALANCED,
    "orchestrator": SpeedRequirement.THOROUGH,
    "specialist": SpeedRequirement.BALANCED,
    "auditor": SpeedRequirement.BALANCED,
    "mentor": SpeedRequirement.THOROUGH,
    "devops": SpeedRequirement.BALANCED,
    "monitoring": SpeedRequirement.FAST,
}

COMPLEXITY_MAP: dict[str, int] = {
    "trivial": 1,
    "simple": 3,
    "medium": 5,
    "complex": 7,
    "critical": 9,
}

RISK_TO_COMPLEXITY_BOOST: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

CONTEXT_MAP: dict[str, ContextSize] = {
    "gatekeeper": ContextSize.SMALL,
    "validator": ContextSize.SMALL,
    "orchestrator": ContextSize.LARGE,
    "specialist": ContextSize.LARGE,
    "auditor": ContextSize.MEDIUM,
    "mentor": ContextSize.MEDIUM,
    "devops": ContextSize.MEDIUM,
    "monitoring": ContextSize.MEDIUM,
}


class TaskProfileBuilder:
    def __init__(self, router: ModelRouter, db_session=None):
        self.router = router
        self._db_session = db_session

    def build(
        self,
        agent_name: str,
        task: Task | None = None,
        task_spec: dict | None = None,
        complexity: str | None = None,
        risk_level: str | None = None,
        is_retry: bool = False,
        previous_model: str | None = None,
        requires_tools: bool = False,
    ) -> TaskProfile:
        task_type = AGENT_TO_TASK_TYPE.get(agent_name, TaskType.PLANNING)
        speed = AGENT_TO_SPEED.get(agent_name, SpeedRequirement.BALANCED)
        context_size = CONTEXT_MAP.get(agent_name, ContextSize.MEDIUM)

        base_complexity = 5
        if complexity:
            base_complexity = COMPLEXITY_MAP.get(complexity, 5)
        if risk_level:
            base_complexity += RISK_TO_COMPLEXITY_BOOST.get(risk_level, 0)
        base_complexity = min(10, max(1, base_complexity))

        budget_usd = 1.0
        if agent_name == "orchestrator" or agent_name == "mentor":
            budget_usd = 2.0
        elif agent_name == "gatekeeper" or agent_name == "monitoring":
            budget_usd = 0.5

        return TaskProfile(
            task_type=task_type,
            complexity=base_complexity,
            context_size=context_size,
            speed_requirement=speed,
            budget_usd=budget_usd,
            is_retry=is_retry,
            previous_model=previous_model,
            requires_tools=requires_tools,
            priority=self._determine_priority(agent_name, risk_level),
        )

    def build_from_task(
        self,
        agent_name: str,
        task: Task,
        requires_tools: bool = False,
    ) -> TaskProfile:
        complexity = getattr(task, "risk_level", "medium")
        risk_level = getattr(task, "risk_level", "medium")
        is_retry = (task.retries or 0) > 0

        return self.build(
            agent_name=agent_name,
            task=task,
            complexity=complexity,
            risk_level=risk_level,
            is_retry=is_retry,
            requires_tools=requires_tools,
        )

    def select_model(self, agent_name: str, task_profile: TaskProfile):
        selection = self.router.select(task_profile)
        return selection

    def select_validation_model(self):
        profile = self.build(
            agent_name="validator",
            complexity="medium",
            risk_level="medium",
        )
        profile.task_type = TaskType.CLASSIFICATION
        return self.router.select(profile)

    def _determine_priority(
        self, agent_name: str, risk_level: str | None
    ) -> str:
        if agent_name == "mentor":
            return "HIGH"
        if risk_level == "critical":
            return "HIGH"
        if risk_level == "high":
            return "HIGH"
        return "MEDIUM"
