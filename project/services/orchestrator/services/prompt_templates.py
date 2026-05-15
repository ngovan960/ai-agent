import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "agents" / "prompts"

SYSTEM_PROMPTS = {
    "gatekeeper": """You are the Gatekeeper Agent of the AI SDLC System.
Your job is to parse user requests, classify complexity, and decide routing.
Respond ONLY with valid JSON. No other text.""",

    "orchestrator": """You are the Orchestrator Agent of the AI SDLC System.
Your job is to break down tasks, identify dependencies, and assign to agents.
Respond ONLY with valid JSON. No other text.""",

    "specialist": """You are the Specialist (Coder) Agent of the AI SDLC System.
Your job is to write code according to the task specification.
Output code files with FILE: markers. Follow all architectural laws.""",

    "auditor": """You are the Auditor (Reviewer) Agent of the AI SDLC System.
Your job is to review code against spec, check architecture, and deliver verdict.
Respond ONLY with valid JSON. No other text.""",

    "mentor": """You are the Supreme Mentor Agent of the AI SDLC System.
You are called for final decisions on escalated tasks.
Your decisions are FINAL. Respond ONLY with valid JSON. No other text.""",

    "devops": """You are the DevOps Agent of the AI SDLC System.
Your job is to build, deploy, and maintain infrastructure.
Respond ONLY with valid JSON. No other text.""",

    "monitoring": """You are the Monitoring Agent of the AI SDLC System.
Your job is to observe, detect anomalies, alert, and suggest improvements.
Respond ONLY with valid JSON. No other text.""",
}


class PromptTemplateLoader:
    """Load and render agent prompt templates.

    Templates are loaded from /agents/prompts/*.txt with variable substitution.
    System prompts provide role context and output format instructions.
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR

    def load_template(self, agent_name: str) -> str:
        """Load raw prompt template for an agent."""
        template_path = self.prompts_dir / f"{agent_name}.txt"
        if template_path.exists():
            return template_path.read_text()
        return self._default_template(agent_name)

    def render(
        self,
        agent_name: str,
        variables: dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Render a prompt template with variable substitution."""
        template = self.load_template(agent_name)
        result = template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def build_messages(
        self,
        agent_name: str,
        variables: dict[str, Any],
        system_prompt: Optional[str] = None,
        context_sections: Optional[list[dict[str, str]]] = None,
    ) -> list[dict]:
        """Build complete messages array for LLM call.

        Returns a list of message dicts suitable for LiteLLM:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
        """
        system = system_prompt or SYSTEM_PROMPTS.get(agent_name, "")
        user_prompt = self.render(agent_name, variables)
        messages = []

        if system:
            messages.append({"role": "system", "content": system.strip()})

        if context_sections:
            for section in context_sections:
                name = section.get("name", "")
                content = section.get("content", "")
                if content:
                    messages.append({"role": "system", "content": f"## {name}\n{content}"})

        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _default_template(self, agent_name: str) -> str:
        """Provide a minimal default template if the file is missing."""
        defaults = {
            "gatekeeper": "User request: {user_request}\nMemory results: {memory_results}",
            "orchestrator": "Classified task: {classified_task}\nProject state: {project_state}",
            "specialist": "Task spec: {task_spec}\nContext: {context}\nArchitectural laws: {architectural_laws}",
            "auditor": "Code: {code}\nSpec: {spec}\nTest results: {test_results}\nArchitectural laws: {laws}",
            "mentor": "Task history: {task_history}\nConflict details: {conflict_details}\nMemory: {memory}",
            "devops": "Verified code: {verified_code}\nDeployment config: {deployment_config}",
            "monitoring": "Logs: {logs}\nMetrics: {metrics}\nUser feedback: {user_feedback}",
        }
        return defaults.get(agent_name, "Task: {input}")
