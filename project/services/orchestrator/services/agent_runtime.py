import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from services.orchestrator.services.cost_governor import CostGovernor
from shared.config.model_router import ModelRouter, NoModelAvailableError, TaskProfile
from shared.models.registry import CostTracking
from shared.models.task import TaskStatus

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    pass


@dataclass
class AgentExecutionResult:
    agent_name: str
    model_used: str
    llm_path: str
    output: Any
    parsed_output: dict | None = None
    error: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    retry_count: int = 0


@dataclass
class EscalationRecord:
    task_id: UUID
    reason: str
    escalated_at: datetime
    severity: str
    target_state: str


@dataclass
class TakeoverRecord:
    task_id: UUID
    mentor_id: UUID
    action: str
    reason: str
    created_at: datetime


class AgentRuntime:
    def __init__(
        self,
        db_session,
        router: ModelRouter,
        cost_governor: CostGovernor | None = None,
    ):
        self._db = db_session
        self.router = router
        self._cost_governor = cost_governor

    async def execute_agent(
        self,
        agent_name: str,
        task_id: UUID,
        task_profile: TaskProfile,
        variables: dict[str, Any],
        context_sections: list[dict[str, str]] | None = None,
        project_id: UUID | None = None,
    ) -> AgentExecutionResult:
        from services.orchestrator.services.agent_dispatcher import AgentDispatcher
        from services.orchestrator.services.task_profile_builder import AGENT_TO_STATE

        dispatcher = AgentDispatcher(self._db)
        current_state = AGENT_TO_STATE.get(agent_name, agent_name.upper())
        start = datetime.now(UTC)

        model_name = ""
        llm_path = ""

        try:
            selection = self.router.select_within_budget(task_profile, task_profile.budget_usd)
            model_name = selection.primary.name
            llm_path = selection.llm_path.value

            if self._cost_governor:
                alerts = await self._cost_governor.check_cost_alerts(project_id=project_id)
                if alerts:
                    for alert in alerts:
                        if alert.exceeded:
                            logger.warning(f"Cost alert before execution: {alert.message}")

            agent_result = await dispatcher.dispatch(
                task_id=task_id,
                project_id=project_id,
                current_state=current_state,
                variables=variables,
                context_sections=context_sections,
                force_agent=agent_name,
                model_name=model_name,
            )

            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            output = agent_result.content or ""
            parsed = self._parse_output(agent_name, output)
            error = agent_result.error

            await self._track_cost(
                task_id=task_id,
                agent_name=agent_name,
                model=model_name,
                input_tokens=agent_result.input_tokens,
                output_tokens=agent_result.output_tokens,
                cost=agent_result.cost_usd,
                latency_ms=latency,
                status="failed" if error else "success",
            )

            if self._cost_governor and not error:
                await self._cost_governor.track_tokens(
                    task_id=task_id,
                    model=model_name,
                    input_tokens=agent_result.input_tokens,
                    output_tokens=agent_result.output_tokens,
                    cost_usd=agent_result.cost_usd,
                    latency_ms=int(latency),
                    agent_name=agent_name,
                )

            return AgentExecutionResult(
                agent_name=agent_name,
                model_used=model_name,
                llm_path=llm_path,
                output=output,
                parsed_output=parsed,
                error=error,
                tokens_used=agent_result.input_tokens,
                cost_usd=agent_result.cost_usd,
                latency_ms=latency,
            )

        except NoModelAvailableError as e:
            logger.error(f"No model available for {agent_name}: {e}")
            return AgentExecutionResult(
                agent_name=agent_name, model_used="", llm_path="", output="", error=str(e),
            )

        except BudgetExceededError as e:
            logger.error(f"Budget exceeded for {agent_name}: {e}")
            return AgentExecutionResult(
                agent_name=agent_name, model_used="", llm_path="", output="", error=str(e),
            )

        except Exception as e:
            logger.exception(f"Agent execution failed for {agent_name}: {e}")
            return AgentExecutionResult(
                agent_name=agent_name, model_used=model_name, llm_path=llm_path,
                output="", error=str(e),
            )

    async def retry_agent(
        self,
        agent_name: str,
        task_id: UUID,
        task_profile: TaskProfile,
        variables: dict[str, Any],
        previous_output: str,
        error: str,
    ) -> AgentExecutionResult:
        retry_variables = dict(variables)
        retry_variables["previous_error"] = error
        retry_variables["previous_output"] = previous_output
        retry_variables["retry_guidance"] = (
            f"Previous attempt failed because: {error}. "
            f"Please fix the issues and try again."
        )

        retry_profile = TaskProfile(
            task_type=task_profile.task_type,
            complexity=task_profile.complexity,
            context_size=task_profile.context_size,
            speed_requirement=task_profile.speed_requirement,
            budget_usd=task_profile.budget_usd,
            is_retry=True,
            previous_model=task_profile.previous_model,
            requires_tools=task_profile.requires_tools,
            priority=task_profile.priority,
        )

        result = await self.execute_agent(
            agent_name=agent_name,
            task_id=task_id,
            task_profile=retry_profile,
            variables=retry_variables,
        )
        result.retry_count = 1
        return result

    async def escalate_task(
        self,
        task_id: UUID,
        reason: str,
        severity: str = "MEDIUM",
    ) -> EscalationRecord:
        from services.orchestrator.services.tasks import transition_task_state
        from shared.schemas.task import StateTransitionRequest

        record = EscalationRecord(
            task_id=task_id,
            reason=reason,
            escalated_at=datetime.now(UTC),
            severity=severity,
            target_state="ESCALATED",
        )

        try:
            await transition_task_state(
                db=self._db,
                task_id=task_id,
                request=StateTransitionRequest(
                    target_status=TaskStatus.ESCALATED,
                    reason=reason,
                ),
            )
        except Exception as e:
            logger.error(f"Escalation transition failed for {task_id}: {e}")

        logger.warning(f"Task {task_id} escalated: {reason} (severity={severity})")
        return record

    async def takeover(
        self,
        task_id: UUID,
        mentor_id: UUID,
        action: str,
        reason: str,
    ) -> TakeoverRecord:
        from services.orchestrator.services.mentor_service import MentorAction, mentor_takeover

        mentor_action = (
            MentorAction(action)
            if isinstance(action, str) and action in [e.value for e in MentorAction]
            else MentorAction.OVERRIDE
        )
        success, msg, result = await mentor_takeover(
            db=self._db,
            task_id=task_id,
            mentor_id=str(mentor_id),
            action=mentor_action,
            reason=reason,
        )

        record = TakeoverRecord(
            task_id=task_id, mentor_id=mentor_id, action=action, reason=reason,
            created_at=datetime.now(UTC),
        )

        logger.info(f"Mentor takeover: task={task_id} action={action} reason={reason} (success={success})")
        return record

    def _parse_output(self, agent_name: str, output: str) -> dict | None:
        if not output or not output.strip():
            return None

        text = output.strip()
        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                return json.loads(text[json_start : json_end + 1])
            except json.JSONDecodeError:
                pass

        if agent_name == "specialist":
            return {"raw_code": text}
        return {"raw_output": text}

    async def _track_cost(
        self, task_id: UUID, agent_name: str, model: str,
        input_tokens: int, output_tokens: int, cost: float, latency_ms: float, status: str,
    ) -> None:
        try:
            tracking = CostTracking(
                task_id=task_id, agent_name=agent_name, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens,
                cost_usd=cost, latency_ms=latency_ms, status=status,
            )
            self._db.add(tracking)
            await self._db.flush()
        except Exception as e:
            logger.warning(f"Cost tracking failed: {e}")
