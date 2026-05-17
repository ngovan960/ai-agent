import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class DevOpsService:
    def __init__(self, db_session, runtime: Any, profile_builder: Any):
        self._db = db_session
        self.runtime = runtime
        self.profile_builder = profile_builder

    async def execute(
        self, task_id: UUID, task: dict, config: dict
    ) -> dict:
        profile = self.profile_builder.build(
            agent_name="devops",
            complexity=task.get("complexity", "medium"),
            risk_level=task.get("risk_level", "medium"),
            requires_tools=True,
        )

        prompt_parts = [
            f"Code/Task: {json.dumps(task, default=str)}",
            f"Deployment Config: {json.dumps(config, default=str)}",
        ]
        full_prompt = "\n\n".join(prompt_parts)

        from services.execution.opencode_cli import OpenCodeCLIRunner
        runner = OpenCodeCLIRunner(project_root=".")
        cli_result = await runner.execute(full_prompt)

        return {
            "status": cli_result.status,
            "output": cli_result.output,
            "model_used": "opencode-cli",
            "cost_usd": 0.0,
            "error": cli_result.error,
        }

    async def build_image(self, task_id: UUID, code_path: str, version: str) -> str:
        import asyncio
        try:
            tag = f"ai-sdlc:{version}"
            process = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", tag, "-f", "Dockerfile", ".",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=120
            )
            if process.returncode == 0:
                return tag
            raise RuntimeError(f"Docker build failed: {stderr.decode()}")
        except TimeoutError:
            logger.error(f"Docker build timed out for task {task_id}")
            raise RuntimeError("Docker build timed out after 120s")
        except Exception as e:
            logger.error(f"Build image failed: {e}")
            raise

    async def deploy_staging(self, image_tag: str) -> dict:
        import asyncio
        try:
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "up", "-d",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=60
            )
            return {"status": "deployed", "image": image_tag, "output": stdout.decode()}
        except TimeoutError:
            return {"status": "failed", "error": "docker-compose timed out after 60s"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
