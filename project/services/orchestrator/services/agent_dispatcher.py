import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.llm.circuit_breaker import CircuitBreaker
from shared.llm.rate_limiter import RateLimiter
from shared.llm.cost_tracker import CostTracker
from services.orchestrator.services.llm_gateway import LLMGateway, LLMResult
from services.orchestrator.services.prompt_templates import PromptTemplateLoader

logger = logging.getLogger(__name__)

STATE_AGENT_MAP: dict[str, str] = {
    "NEW": "gatekeeper",
    "ANALYZING": "orchestrator",
    "PLANNING": "orchestrator",
    "IMPLEMENTING": "specialist",
    "VERIFYING": "system",
    "REVIEWING": "auditor",
    "ESCALATED": "mentor",
    "BLOCKED": "orchestrator",
    "FAILED": "mentor",
}


AGENT_CONFIG: dict[str, dict] = {
    "gatekeeper": {
        "primary_model": "deepseek_v4_flash",
        "temperature": 0.1,
        "max_tokens": 2048,
        "timeout": 15,
        "output_format": "json",
    },
    "orchestrator": {
        "primary_model": "qwen_3_6_plus",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 60,
        "output_format": "json",
    },
    "specialist": {
        "primary_model": "deepseek_v4_pro",
        "temperature": 0.1,
        "max_tokens": 8192,
        "timeout": 90,
        "output_format": "text",
    },
    "auditor": {
        "primary_model": "qwen_3_5_plus",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 60,
        "output_format": "json",
    },
    "mentor": {
        "primary_model": "qwen_3_6_plus",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 90,
        "output_format": "json",
    },
    "devops": {
        "primary_model": "deepseek_v4_pro",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 60,
        "output_format": "json",
    },
    "monitoring": {
        "primary_model": "deepseek_v4_flash",
        "temperature": 0.1,
        "max_tokens": 2048,
        "timeout": 15,
        "output_format": "json",
    },
}


@dataclass
class AgentDispatchResult:
    """Result from dispatching a task to an agent."""
    agent_name: str
    model_used: str
    content: str
    parsed_output: dict[str, Any] | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    status: str
    error: Optional[str] = None


class AgentDispatcher:
    """Route tasks to the appropriate agent and execute them via LLM Gateway.

    The dispatcher:
    1. Determines which agent should handle the task based on current state
    2. Selects model configuration for the agent
    3. Builds context via ContextBuilder
    4. Loads and renders prompt template
    5. Calls LLMGateway with assembled messages
    6. Parses agent response
    7. Returns structured result
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_gateway: Optional[LLMGateway] = None,
        prompt_loader: Optional[PromptTemplateLoader] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.db = db
        self.llm_gateway = llm_gateway or LLMGateway(
            db, circuit_breaker=circuit_breaker, rate_limiter=rate_limiter
        )
        self.prompt_loader = prompt_loader or PromptTemplateLoader()
        self.cost_tracker = CostTracker(db)

    def get_agent_for_state(self, state: str) -> str:
        """Get the agent name for a given task state."""
        return STATE_AGENT_MAP.get(state, "gatekeeper")

    def get_agent_config(self, agent_name: str) -> dict:
        """Get configuration for an agent."""
        return AGENT_CONFIG.get(agent_name, AGENT_CONFIG["gatekeeper"])

    async def dispatch(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        current_state: str,
        variables: dict[str, Any],
        context_sections: Optional[list[dict[str, str]]] = None,
        force_agent: Optional[str] = None,
    ) -> AgentDispatchResult:
        """Dispatch a task to the appropriate agent for execution."""
        agent_name = force_agent or self.get_agent_for_state(current_state)
        config = self.get_agent_config(agent_name)

        messages = self.prompt_loader.build_messages(
            agent_name=agent_name,
            variables=variables,
            context_sections=context_sections,
        )

        result = await self.llm_gateway.call(
            task_id=task_id,
            project_id=project_id,
            agent_name=agent_name,
            messages=messages,
            model_preference=config.get("primary_model"),
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.1),
            timeout=config.get("timeout", 60),
        )

        parsed_output = self._parse_output(agent_name, result.content)

        return AgentDispatchResult(
            agent_name=agent_name,
            model_used=result.model,
            content=result.content,
            parsed_output=parsed_output,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            status=result.status,
            error=result.error,
        )

    async def dispatch_gatekeeper(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        user_request: str,
        memory_results: Optional[dict] = None,
    ) -> AgentDispatchResult:
        """Run Gatekeeper classification on a user request."""
        variables = {
            "user_request": user_request,
            "memory_results": json.dumps(memory_results or {}, default=str),
        }
        return await self.dispatch(
            task_id=task_id,
            project_id=project_id,
            current_state="NEW",
            variables=variables,
            force_agent="gatekeeper",
        )

    async def dispatch_orchestrator(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        classified_task: dict,
        project_state: dict,
    ) -> AgentDispatchResult:
        """Run Orchestrator planning on a classified task."""
        variables = {
            "classified_task": json.dumps(classified_task, default=str),
            "project_state": json.dumps(project_state, default=str),
        }
        return await self.dispatch(
            task_id=task_id,
            project_id=project_id,
            current_state="ANALYZING",
            variables=variables,
            force_agent="orchestrator",
        )

    async def dispatch_specialist(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        task_spec: dict,
        context: dict,
        architectural_laws: Optional[str] = None,
    ) -> AgentDispatchResult:
        """Run Specialist code generation."""
        variables = {
            "task_spec": json.dumps(task_spec, default=str, indent=2),
            "context": json.dumps(context, default=str, indent=2),
            "architectural_laws": architectural_laws or "",
        }
        return await self.dispatch(
            task_id=task_id,
            project_id=project_id,
            current_state="IMPLEMENTING",
            variables=variables,
            force_agent="specialist",
        )

    async def dispatch_auditor(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        code: str,
        spec: dict,
        test_results: dict,
        laws: Optional[str] = None,
    ) -> AgentDispatchResult:
        """Run Auditor code review."""
        variables = {
            "code": code[:30000],
            "spec": json.dumps(spec, default=str),
            "test_results": json.dumps(test_results, default=str),
            "laws": laws or "",
        }
        return await self.dispatch(
            task_id=task_id,
            project_id=project_id,
            current_state="REVIEWING",
            variables=variables,
            force_agent="auditor",
        )

    async def dispatch_mentor(
        self,
        task_id: UUID,
        project_id: Optional[UUID],
        task_history: dict,
        conflict_details: dict,
        memory: Optional[dict] = None,
    ) -> AgentDispatchResult:
        """Run Mentor decision on an escalated task."""
        variables = {
            "task_history": json.dumps(task_history, default=str),
            "conflict_details": json.dumps(conflict_details, default=str),
            "memory": json.dumps(memory or {}, default=str),
        }
        return await self.dispatch(
            task_id=task_id,
            project_id=project_id,
            current_state="ESCALATED",
            variables=variables,
            force_agent="mentor",
        )

    @staticmethod
    def _parse_output(agent_name: str, content: str) -> dict[str, Any] | None:
        """Parse agent output. Returns parsed JSON dict or None for text output."""
        if not content:
            return None

        config = AGENT_CONFIG.get(agent_name, {})
        if config.get("output_format") != "json":
            return None

        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse {agent_name} output as JSON: {e}")

        return None
