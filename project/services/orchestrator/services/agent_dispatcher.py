import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services.llm_gateway import LLMGateway
from services.orchestrator.services.prompt_templates import PromptTemplateLoader
from shared.llm.circuit_breaker import CircuitBreaker
from shared.llm.cost_tracker import CostTracker
from shared.llm.rate_limiter import RateLimiter

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
    agent_name: str
    model_used: str
    content: str
    parsed_output: dict[str, Any] | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    status: str
    error: str | None = None


class AgentDispatcher:
    def __init__(
        self,
        db: AsyncSession,
        llm_gateway: LLMGateway | None = None,
        prompt_loader: PromptTemplateLoader | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.db = db
        self.llm_gateway = llm_gateway or LLMGateway(
            db, circuit_breaker=circuit_breaker, rate_limiter=rate_limiter
        )
        self.prompt_loader = prompt_loader or PromptTemplateLoader()
        self.cost_tracker = CostTracker(db)

    def get_agent_for_state(self, state: str) -> str:
        return STATE_AGENT_MAP.get(state, "gatekeeper")

    def get_agent_config(self, agent_name: str) -> dict:
        return AGENT_CONFIG.get(agent_name, AGENT_CONFIG["gatekeeper"])

    async def dispatch(
        self,
        task_id: UUID,
        project_id: UUID | None,
        current_state: str,
        variables: dict[str, Any],
        context_sections: list[dict[str, str]] | None = None,
        force_agent: str | None = None,
        model_name: str | None = None,
    ) -> AgentDispatchResult:
        agent_name = force_agent or self.get_agent_for_state(current_state)
        config = self.get_agent_config(agent_name)

        messages = self.prompt_loader.build_messages(
            agent_name=agent_name,
            variables=variables,
            context_sections=context_sections,
            model_name=model_name,
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
        self, task_id: UUID, project_id: UUID | None, user_request: str, memory_results: dict | None = None,
    ) -> AgentDispatchResult:
        variables = {"user_request": user_request, "memory_results": json.dumps(memory_results or {}, default=str)}
        return await self.dispatch(task_id=task_id, project_id=project_id, current_state="NEW", variables=variables, force_agent="gatekeeper")

    async def dispatch_orchestrator(
        self, task_id: UUID, project_id: UUID | None, classified_task: dict, project_state: dict,
    ) -> AgentDispatchResult:
        variables = {"classified_task": json.dumps(classified_task, default=str), "project_state": json.dumps(project_state, default=str)}
        return await self.dispatch(task_id=task_id, project_id=project_id, current_state="ANALYZING", variables=variables, force_agent="orchestrator")

    async def dispatch_specialist(
        self, task_id: UUID, project_id: UUID | None, task_spec: dict, context: dict, architectural_laws: str | None = None,
    ) -> AgentDispatchResult:
        variables = {"task_spec": json.dumps(task_spec, default=str, indent=2), "context": json.dumps(context, default=str, indent=2), "architectural_laws": architectural_laws or ""}
        return await self.dispatch(task_id=task_id, project_id=project_id, current_state="IMPLEMENTING", variables=variables, force_agent="specialist")

    async def dispatch_auditor(
        self, task_id: UUID, project_id: UUID | None, code: str, spec: dict, test_results: dict, laws: str | None = None,
    ) -> AgentDispatchResult:
        variables = {"code": code[:30000], "spec": json.dumps(spec, default=str), "test_results": json.dumps(test_results, default=str), "laws": laws or ""}
        return await self.dispatch(task_id=task_id, project_id=project_id, current_state="REVIEWING", variables=variables, force_agent="auditor")

    async def dispatch_mentor(
        self, task_id: UUID, project_id: UUID | None, task_history: dict, conflict_details: dict, memory: dict | None = None,
    ) -> AgentDispatchResult:
        variables = {"task_history": json.dumps(task_history, default=str), "conflict_details": json.dumps(conflict_details, default=str), "memory": json.dumps(memory or {}, default=str)}
        return await self.dispatch(task_id=task_id, project_id=project_id, current_state="ESCALATED", variables=variables, force_agent="mentor")

    @staticmethod
    def _parse_output(agent_name: str, content: str) -> dict[str, Any] | None:
        if not content:
            return None
        config = AGENT_CONFIG.get(agent_name, {})
        if config.get("output_format") != "json":
            return None
        idx = 0
        while True:
            start = content.find("{", idx)
            if start == -1:
                break
            end = content.rfind("}")
            if end > start:
                try:
                    return json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    pass
            idx = start + 1
        return None
