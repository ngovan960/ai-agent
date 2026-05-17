import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "agents" / "prompts"

SELF_AWARENESS_PROMPTS = {
    "deepseek_v4_flash": "SELF-AWARENESS: You are DeepSeek V4 Flash - fastest model, best for classification, low cost.",
    "deepseek_v4_pro": "SELF-AWARENESS: You are DeepSeek V4 Pro - strong code generation, 1M context, balanced.",
    "qwen_3_5_plus": "SELF-AWARENESS: You are Qwen 3.5 Plus - balanced capabilities, strong at code review.",
    "qwen_3_6_plus": "SELF-AWARENESS: You are Qwen 3.6 Plus - best strategic reasoning, planning specialist.",
    "minimax_m2_7": "SELF-AWARENESS: You are MiniMax M2.7 - cost-effective, fast, good for monitoring.",
}


PROMPT_VERSIONS: dict[str, int] = {
    "gatekeeper": 2, "validator": 1, "orchestrator": 1,
    "specialist": 2, "auditor": 2, "mentor": 1,
    "devops": 1, "monitoring": 1, "coder": 2, "reviewer": 2,
}


class PromptTemplateLoader:
    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self._cache: dict[str, str] = {}

    def get_prompt_version(self, agent_name: str) -> int:
        return PROMPT_VERSIONS.get(agent_name, 1)

    def load_template(self, agent_name: str) -> str:
        # Map legacy/duplicate names to canonical ones
        if agent_name == "coder":
            agent_name = "specialist"
        elif agent_name == "reviewer":
            agent_name = "auditor"

        if agent_name in self._cache:
            return self._cache[agent_name]
        path = self.template_dir / f"{agent_name}.txt"
        if not path.exists():
            logger.warning(f"Template not found: {path}")
            return f"You are the {agent_name.capitalize()} Agent. Execute your task."
        content = path.read_text(encoding="utf-8")
        self._cache[agent_name] = content
        return content

    def render(self, agent_name: str, variables: dict[str, str]) -> str:
        template = self.load_template(agent_name)
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template

    def inject_self_awareness(self, model_name: str, system_prompt: str) -> str:
        awareness = SELF_AWARENESS_PROMPTS.get(model_name)
        if awareness:
            return f"{awareness}\n\n{system_prompt}"
        return system_prompt

    def build_messages(
        self,
        agent_name: str,
        variables: dict[str, str],
        context_sections: list[dict[str, str]] | None = None,
        model_name: str | None = None,
    ) -> list[dict[str, str]]:
        system_prompt = self.load_template(agent_name)
        if model_name:
            system_prompt = self.inject_self_awareness(model_name, system_prompt)
        messages = [{"role": "system", "content": system_prompt}]
        if context_sections:
            for section in context_sections:
                content = section.get("content", "")
                if content:
                    messages.append({"role": "system", "content": f"=== {section.get('name', 'Context')} ===\n{content}"})
        user_content = self._build_user_content(agent_name, variables)
        messages.append({"role": "user", "content": user_content})
        return messages

    def _build_user_content(self, agent_name: str, variables: dict[str, str]) -> str:
        user_template_path = self.template_dir / f"{agent_name}_user.txt"
        if user_template_path.exists():
            template = user_template_path.read_text(encoding="utf-8")
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))
            return template
        parts = [f"{k}: {v}" for k, v in variables.items() if v]
        return "\n\n".join(parts) if parts else "Execute the task."
