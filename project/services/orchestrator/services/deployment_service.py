import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class DeploymentService:
    def __init__(self, db_session: Any = None, runtime: Any = None, profile_builder: Any = None):
        self._db = db_session
        self.runtime = runtime
        self.profile_builder = profile_builder
        self._audit_log: list[dict] = []
        if db_session is None:
            logger.warning("DeploymentService initialized without db_session — DB-dependent features will be unavailable")

    async def _run_subprocess(self, cmd: list[str], timeout: int = 120, cwd: str | None = None) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, stdout.decode(), stderr.decode()
        except TimeoutError:
            proc.kill()
            raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from None

    async def build_image(self, code_path: str, version: str) -> str:
        tag = f"ai-sdlc:{version}"
        try:
            rc, stdout, stderr = await self._run_subprocess(
                ["docker", "build", "-t", tag, "-f", "Dockerfile", code_path],
                timeout=300,
            )
            if rc == 0:
                logger.info(f"Image built: {tag}")
                return tag
            raise RuntimeError(f"Docker build failed: {stderr}")
        except Exception as e:
            logger.error(f"Build image failed: {e}")
            raise

    async def _log_and_return(self, deployment_id: str, image_tag: str, status: str, output: str, error: str | None = None, staging_url: str = "http://localhost:8000") -> dict:
        self._log_deployment({
            "deployment_id": deployment_id,
            "type": "staging",
            "image": image_tag,
            "status": status,
            "output": output[:2000],
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        return {
            "deployment_id": deployment_id,
            "status": status,
            "image": image_tag,
            "staging_url": staging_url,
            "output": output[:1000],
            "error": error,
        }

    async def deploy_staging(self, image_tag: str, code_path: str | None = None, staging_host: str = "localhost", staging_port: int = 8081) -> dict:
        deployment_id = str(uuid4())
        staging_url = f"http://{staging_host}:{staging_port}"
        workdir = code_path or os.getcwd()
        compose_file = os.path.join(workdir, "docker-compose.yml")
        try:
            rc, stdout, stderr = await self._run_subprocess(
                ["docker", "compose", "-f", compose_file, "-p", "ai-sdlc-staging", "up", "-d"],
                timeout=120,
                cwd=workdir,
            )
            status = "deployed" if rc == 0 else "failed"
            return await self._log_and_return(deployment_id, image_tag, status, stdout if rc == 0 else stderr, stderr if rc != 0 else None, staging_url)
        except Exception as e:
            return await self._log_and_return(deployment_id, image_tag, "failed", str(e), str(e), staging_url)

    async def verify_staging(self, staging_url: str) -> dict:
        checks = {}
        endpoints = [
            ("health", f"{staging_url}/health"),
            ("api", f"{staging_url}/api/v1/projects/"),
            ("docs", f"{staging_url}/docs"),
        ]
        all_passed = True
        async with httpx.AsyncClient(timeout=15.0) as client:
            for name, url in endpoints:
                try:
                    resp = await client.get(url)
                    passed = 200 <= resp.status_code < 400
                    checks[name] = {"passed": passed, "status": resp.status_code}
                    if not passed:
                        all_passed = False
                except Exception as e:
                    checks[name] = {"passed": False, "error": str(e)}
                    all_passed = False
        return {
            "all_passed": all_passed,
            "checks": checks,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def verify_production(self, production_url: str) -> dict:
        return await self.verify_staging(production_url)

    def _log_deployment(self, info: dict) -> None:
        self._audit_log.append(info)
        logger.info(f"Deployment logged: {info.get('deployment_id')} -> {info.get('status')}")

    def get_deployment_log(self, deployment_id: str) -> dict | None:
        for entry in self._audit_log:
            if entry["deployment_id"] == deployment_id:
                return entry
        return None

    def get_all_deployments(self) -> list[dict]:
        return self._audit_log.copy()
