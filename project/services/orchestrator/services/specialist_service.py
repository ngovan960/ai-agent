import json
import logging
from typing import Any
from uuid import UUID

from shared.config.model_router import ModelRouter

logger = logging.getLogger(__name__)


class SpecialistService:
    def __init__(self, db_session, runtime: Any, router: ModelRouter, profile_builder: Any):
        self._db = db_session
        self.runtime = runtime
        self.router = router
        self.profile_builder = profile_builder

    async def execute(
        self,
        task_id: UUID,
        task_spec: dict,
        context: dict,
        architectural_laws: str | None = None,
    ) -> dict:
        profile = self.profile_builder.build(
            agent_name="specialist",
            complexity=task_spec.get("complexity", "medium"),
            risk_level=task_spec.get("risk_level", "medium"),
            requires_tools=True,
        )

        from services.orchestrator.services.prompt_templates import PromptTemplateLoader
        loader = PromptTemplateLoader()
        rendered_prompt = loader.render("specialist", {
            "task_spec": json.dumps(task_spec, default=str, indent=2),
            "context": json.dumps(context, default=str, indent=2),
            "architectural_laws": architectural_laws or ""
        })

        prompt_parts = [
            rendered_prompt
        ]
            
        context_sections = self._build_codegen_context(task_spec, context)
        for section in context_sections:
            prompt_parts.append(f"=== {section['name']} ===\n{section['content']}")
            
        full_prompt = "\n\n".join(prompt_parts)

        from services.execution.opencode_cli import OpenCodeCLIRunner
        runner = OpenCodeCLIRunner(project_root=".")
        cli_result = await runner.execute(full_prompt)
        
        files_written = self._extract_files(cli_result.output)

        return {
            "status": cli_result.status,
            "output": cli_result.output,
            "files_created": files_written["created"],
            "files_modified": files_written["modified"],
            "model_used": "opencode-cli",
            "cost_usd": 0.0,
            "latency_ms": cli_result.duration_ms,
            "error": cli_result.error,
        }

    async def design_module(
        self, task_id: UUID, module_spec: dict
    ) -> dict:
        return await self.execute(
            task_id=task_id, task_spec=module_spec, context={}
        )

    def _build_codegen_context(
        self, task_spec: dict, context: dict
    ) -> list[dict[str, str]]:
        sections = []
        project_structure = context.get("project_structure", "")
        if project_structure:
            sections.append({"name": "Project Structure", "content": project_structure})

        conventions = context.get("conventions", "")
        if conventions:
            sections.append({"name": "Code Conventions", "content": conventions})

        constraints = task_spec.get("constraints", [])
        if constraints:
            sections.append(
                {"name": "Constraints", "content": json.dumps(constraints, indent=2)}
            )

        return sections

    def _extract_files(self, output: str) -> dict:
        import re

        created = []
        modified = []
        file_pattern = r"(?:CREATE|FILE|WRITE)\s*[=:]\s*(\S+)"
        matches = re.findall(file_pattern, output, re.IGNORECASE)
        for m in matches:
            p = m.strip().strip("'\"")
            if p and p not in created:
                created.append(p)
        return {"created": created, "modified": modified}
