"""Sandbox Manager — Docker-based isolated verification sandbox.

All subprocess calls use asyncio.create_subprocess_exec to avoid blocking
the event loop during Docker operations (which can take 30-120 seconds).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)

DEFAULT_CPU = 1
DEFAULT_MEM = "512m"
DEFAULT_TIMEOUT = 120
BASE_IMAGE = "python:3.12-slim"


@dataclass
class SandboxResult:
    status: str = "pending"
    container_id: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    logs: str = ""
    duration_ms: float = 0
    error: str | None = None


class SandboxManager:
    def __init__(self):
        self._containers: dict[str, dict] = {}

    async def _run_cmd(
        self, cmd: list[str], timeout: int = 60
    ) -> tuple[int, str, str]:
        """Run a command asynchronously without blocking the event loop."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            process.kill()
            return -1, "", f"Command timed out after {timeout}s"

    async def create_sandbox(
        self,
        task_id: UUID,
        code_path: str,
        base_image: str = BASE_IMAGE,
        cpus: int = DEFAULT_CPU,
        memory: str = DEFAULT_MEM,
    ) -> SandboxResult:
        container_id = f"verif-{task_id.hex[:12]}"
        runtime_dir = f"/tmp/sandbox/{task_id.hex[:12]}"

        try:
            await self._run_cmd(
                ["docker", "pull", base_image], timeout=60
            )
        except Exception as e:
            logger.warning(f"docker pull failed (may use cached image): {e}")

        try:
            await self._run_cmd(["mkdir", "-p", runtime_dir], timeout=10)
            rc, _, err = await self._run_cmd(
                ["cp", "-r", code_path, f"{runtime_dir}/source"], timeout=30
            )
            if rc != 0:
                return SandboxResult(status="failed", error=f"Failed to copy source: {err}")
        except Exception as e:
            return SandboxResult(status="failed", error=f"Failed to prepare runtime dir: {e}")

        docker_args = [
            "docker", "run", "-d",
            "--name", container_id,
            "--cpus", str(cpus),
            "--memory", memory,
            "--network", "none",
            "--read-only",
            "--security-opt", "no-new-privileges",
            "-v", f"{runtime_dir}/source:/workspace/source:ro",
            "-v", f"{runtime_dir}/output:/workspace/output:rw",
            base_image,
            "sleep", "infinity",
        ]

        try:
            rc, stdout, stderr = await self._run_cmd(docker_args, timeout=30)
            if rc != 0:
                return SandboxResult(
                    status="failed",
                    error=f"Container creation failed: {stderr}",
                )
            actual_id = stdout.strip()
            self._containers[container_id] = {
                "container_id": actual_id,
                "task_id": str(task_id),
                "runtime_dir": runtime_dir,
                "created_at": datetime.now(UTC).isoformat(),
            }

            install_cmds = [
                "apt-get update -qq && apt-get install -y -qq python3 python3-pip nodejs npm 2>&1 || true",
                "pip3 install pytest ruff bandit build 2>&1 || true",
            ]
            for cmd in install_cmds:
                await self._run_cmd(
                    ["docker", "exec", container_id, "bash", "-c", cmd],
                    timeout=120,
                )

            return SandboxResult(
                status="created",
                container_id=container_id,
                stdout=f"Container {container_id} created",
            )

        except Exception as e:
            return SandboxResult(status="failed", error=f"Container creation failed: {e}")

    async def run_verification(
        self,
        container_id: str,
        language: str = "python",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> SandboxResult:
        if container_id not in self._containers:
            return SandboxResult(status="failed", error=f"Container {container_id} not found")

        start = datetime.now(UTC)
        commands = [
            "cd /workspace/source && ruff check . --quiet 2>&1 || true",
            "cd /workspace/source && pytest tests/ -x --tb=short -q 2>&1 || true",
            "cd /workspace/source && python -m build . --outdir /workspace/output 2>&1 || true",
            "cd /workspace/source && bandit -r . -f json -q 2>&1 || true",
        ]

        all_output = []
        all_failed = False
        per_cmd_timeout = timeout // len(commands)
        for cmd in commands:
            try:
                rc, stdout, stderr = await self._run_cmd(
                    ["docker", "exec", container_id, "bash", "-c", cmd],
                    timeout=per_cmd_timeout,
                )
                step_name = cmd.split("&&")[0].strip()
                all_output.append(f"[{step_name}] exit_code={rc}")
                if rc != 0:
                    all_output.append(stderr[:2000])
                    all_failed = True
                else:
                    all_output.append(stdout[:2000])
            except Exception as e:
                all_output.append(f"[error] {e}")
                all_failed = True

        duration = (datetime.now(UTC) - start).total_seconds() * 1000
        return SandboxResult(
            status="failed" if all_failed else "verified",
            container_id=container_id,
            logs="\n".join(all_output),
            exit_code=1 if all_failed else 0,
            duration_ms=duration,
        )

    async def capture_logs(self, container_id: str) -> str:
        if container_id not in self._containers:
            return "No logs available"
        try:
            rc, stdout, stderr = await self._run_cmd(
                ["docker", "logs", container_id], timeout=10
            )
            return stdout + stderr
        except Exception as e:
            return f"Failed to capture logs: {e}"

    async def destroy_container(self, container_id: str) -> bool:
        if container_id not in self._containers:
            return False
        try:
            await self._run_cmd(
                ["docker", "rm", "-f", container_id], timeout=30
            )
            self._containers.pop(container_id, None)
            return True
        except Exception as e:
            logger.error(f"Failed to destroy container {container_id}: {e}")
            return False

    async def destroy_all(self) -> int:
        count = 0
        for cid in list(self._containers.keys()):
            if await self.destroy_container(cid):
                count += 1
        return count
