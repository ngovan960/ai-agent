"""Sandboxed OpenCode Adapter — Dual-Volume Docker Sandbox (Security Fix #1)

Wraps OpenCode tool operations inside a Docker container with:
- Target project mounted as Read-Write (for code editing)
- Core agent system mounted as Read-Only or NOT mounted at all
- Container runs with --read-only, --network none, --security-opt no-new-privileges
- File operations execute via docker exec, never touch host filesystem directly
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.execution.opencode_adapter import OpenCodeResult

logger = logging.getLogger(__name__)

# Paths that MUST NEVER be mounted into the container (core system)
PROTECTED_PATHS = [
    "shared/config/laws.yaml",
    "shared/config/models.yaml",
    ".env",
    ".env.local",
    "shared/database.py",
    "shared/llm/",
    "services/orchestrator/",
    "services/execution/",
    "agents/prompts/",
    "alembic/",
]

DEFAULT_SANDBOX_IMAGE = "ubuntu:22.04"
DEFAULT_CPU = 2
DEFAULT_MEM = "4g"
DEFAULT_TIMEOUT = 60


@dataclass
class SandboxSession:
    session_id: str
    container_id: str
    task_id: UUID
    target_project_path: str
    created_at: str
    status: str = "active"
    error: str | None = None


class SandboxedOpenCodeAdapter:
    """OpenCode adapter that runs inside a Docker sandbox with dual-volume isolation."""

    def __init__(
        self,
        target_project_path: str | None = None,
        core_system_path: str | None = None,
        sandbox_image: str = DEFAULT_SANDBOX_IMAGE,
        cpus: int = DEFAULT_CPU,
        memory: str = DEFAULT_MEM,
    ):
        self._target_project_path = target_project_path
        self._core_system_path = core_system_path
        self._sandbox_image = sandbox_image
        self._cpus = cpus
        self._memory = memory
        self._sessions: dict[str, SandboxSession] = {}

    def _is_protected_path(self, path: str) -> bool:
        """Check if a path is in the protected core system list."""
        normalized = path.replace("\\", "/").lstrip("/")
        for protected in PROTECTED_PATHS:
            if normalized.startswith(protected) or normalized == protected.rstrip("/"):
                return True
        return False

    async def create_session(self, task_id: UUID) -> SandboxSession:
        """Create a Docker sandbox session for a task."""
        session_id = f"sandbox-{task_id.hex[:12]}"

        if not self._target_project_path:
            session = SandboxSession(
                session_id=session_id,
                container_id="",
                task_id=task_id,
                target_project_path="",
                created_at=datetime.now(UTC).isoformat(),
                status="failed",
                error="No target project path provided",
            )
            return session

        try:
            subprocess.run(
                ["docker", "pull", self._sandbox_image],
                capture_output=True, text=True, timeout=60,
            )
        except Exception:
            logger.warning("docker pull failed (may use cached image)")

        docker_args = [
            "docker", "run", "-d",
            "--name", session_id,
            "--cpus", str(self._cpus),
            "--memory", self._memory,
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m",
            "--security-opt", "no-new-privileges",
            "--security-opt", "seccomp=default",
            "-v", f"{self._target_project_path}:/workspace/project:rw",
        ]

        if self._core_system_path:
            docker_args.extend([
                "-v", f"{self._core_system_path}:/workspace/core:ro",
            ])

        docker_args.extend([
            "-w", "/workspace/project",
            self._sandbox_image,
            "sleep", "infinity",
        ])

        try:
            result = subprocess.run(docker_args, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                session = SandboxSession(
                    session_id=session_id,
                    container_id="",
                    task_id=task_id,
                    target_project_path=self._target_project_path,
                    created_at=datetime.now(UTC).isoformat(),
                    status="failed",
                    error=f"Container creation failed: {result.stderr}",
                )
                return session

            container_id = result.stdout.strip()
            session = SandboxSession(
                session_id=session_id,
                container_id=container_id,
                task_id=task_id,
                target_project_path=self._target_project_path,
                created_at=datetime.now(UTC).isoformat(),
                status="active",
            )
            self._sessions[session_id] = session

            install_cmds = [
                "apt-get update -qq && apt-get install -y -qq python3 python3-pip 2>&1 || true",
                "pip3 install pytest ruff 2>&1 || true",
            ]
            for cmd in install_cmds:
                subprocess.run(
                    ["docker", "exec", container_id, "bash", "-c", cmd],
                    capture_output=True, text=True, timeout=120,
                )

            logger.info(f"Sandbox session created: {session_id} for task {task_id}")
            return session

        except subprocess.TimeoutExpired as e:
            return SandboxSession(
                session_id=session_id, container_id="", task_id=task_id,
                target_project_path=self._target_project_path,
                created_at=datetime.now(UTC).isoformat(),
                status="failed", error=f"Container creation timed out: {e}",
            )
        except Exception as e:
            return SandboxSession(
                session_id=session_id, container_id="", task_id=task_id,
                target_project_path=self._target_project_path,
                created_at=datetime.now(UTC).isoformat(),
                status="failed", error=f"Container creation failed: {e}",
            )

    async def write_file(self, session_id: str, path: str, content: str) -> bool:
        """Write file inside sandbox. Blocks writes to protected paths."""
        session = self._sessions.get(session_id)
        if not session or session.status != "active":
            logger.error(f"Sandbox session {session_id} not active")
            return False

        if self._is_protected_path(path):
            logger.error(f"BLOCKED: Write to protected path: {path}")
            return False

        container_id = session.container_id
        safe_path = f"/workspace/project/{path.lstrip('/')}"

        try:
            escaped_content = content.replace("'", "'\"'\"'")
            cmd = f"mkdir -p $(dirname '{safe_path}') && cat > '{safe_path}' << 'SANDBOX_EOF'\n{escaped_content}\nSANDBOX_EOF"
            result = subprocess.run(
                ["docker", "exec", container_id, "bash", "-c", cmd],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error(f"write_file failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"write_file exception: {e}")
            return False

    async def read_file(self, session_id: str, path: str) -> str | None:
        """Read file inside sandbox. Blocks reads of protected paths."""
        session = self._sessions.get(session_id)
        if not session or session.status != "active":
            return None

        if self._is_protected_path(path):
            logger.error(f"BLOCKED: Read from protected path: {path}")
            return None

        container_id = session.container_id
        safe_path = f"/workspace/project/{path.lstrip('/')}"

        try:
            result = subprocess.run(
                ["docker", "exec", container_id, "cat", safe_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None
            return result.stdout
        except Exception:
            return None

    async def edit_file(self, session_id: str, path: str, old_string: str, new_string: str) -> bool:
        """Edit file inside sandbox using sed-like replacement."""
        content = await self.read_file(session_id, path)
        if content is None:
            return False
        if old_string not in content:
            logger.warning(f"edit_file: old_string not found in {path}")
            return False
        updated = content.replace(old_string, new_string)
        return await self.write_file(session_id, path, updated)

    async def run_bash(self, session_id: str, command: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
        """Run bash command inside sandbox. Blocks dangerous commands."""
        session = self._sessions.get(session_id)
        if not session or session.status != "active":
            return {"stdout": "", "stderr": "Sandbox not active", "exit_code": -1, "success": False}

        # Normalize and check for dangerous patterns (handles spacing tricks, variable expansion)
        import re
        normalized_cmd = re.sub(r'\s+', ' ', command.strip())
        dangerous_patterns = [
            r'rm\s+(-[^\s]*\s+)*/',         # rm with absolute root paths
            r'rm\s+(-[^\s]*\s+)*~',          # rm home directory
            r'>\s*/dev/',                     # redirect to devices
            r'dd\s+if=',                      # disk destroyer
            r'mkfs\b',                        # format filesystem
            r'chmod\s+777\s+/',               # open permissions on root
            r'\bsudo\b',                      # privilege escalation
            r'curl\s.*\|\s*bash',             # pipe curl to bash
            r'wget\s.*\|\s*bash',             # pipe wget to bash
            r'\$\(.*\)',                       # command substitution
            r'`[^`]+`',                       # backtick command substitution
            r'base64\s+(-d|--decode)',         # base64 decode (code execution bypass)
            r'eval\s+',                        # eval arbitrary code
            r'python[23]?\s+-c',              # inline python execution
            r'perl\s+-e',                      # inline perl execution
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, normalized_cmd, re.IGNORECASE):
                logger.error(f"BLOCKED: Dangerous command pattern detected: {command}")
                return {"stdout": "", "stderr": f"Dangerous command blocked: matched pattern", "exit_code": -1, "success": False}

        container_id = session.container_id

        try:
            result = subprocess.run(
                ["docker", "exec", container_id, "bash", "-c", command],
                capture_output=True, text=True, timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Command timed out after {timeout}s", "exit_code": -1, "success": False}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1, "success": False}

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy sandbox session and container."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        try:
            subprocess.run(
                ["docker", "rm", "-f", session.container_id],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            logger.error(f"Failed to destroy container: {e}")

        session.status = "destroyed"
        self._sessions.pop(session_id, None)
        logger.info(f"Sandbox session destroyed: {session_id}")
        return True

    async def destroy_all(self) -> int:
        """Destroy all sandbox sessions."""
        count = 0
        for sid in list(self._sessions.keys()):
            if await self.destroy_session(sid):
                count += 1
        return count

    async def execute(
        self,
        task_id: UUID,
        task_spec: dict,
        context: dict,
    ) -> OpenCodeResult:
        """Full execution pipeline: create sandbox → write files → run verification → destroy."""
        agent_id = uuid4()
        start = datetime.now(UTC)

        session = await self.create_session(task_id)
        if session.status != "active":
            return OpenCodeResult(
                agent_id=agent_id,
                status="failed",
                error=f"Sandbox creation failed: {session.error}",
                duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
            )

        try:
            files_to_create = task_spec.get("files_to_create", [])
            files_to_modify = task_spec.get("files_to_modify", [])
            verification = task_spec.get("verification", "")

            created = []
            for file_path in files_to_create:
                if self._is_protected_path(file_path):
                    logger.error(f"BLOCKED: Attempted to create protected file: {file_path}")
                    continue
                success = await self.write_file(session.session_id, file_path, "")
                if success:
                    created.append(file_path)

            modified = []
            for file_path in files_to_modify:
                if self._is_protected_path(file_path):
                    logger.error(f"BLOCKED: Attempted to modify protected file: {file_path}")
                    continue
                modified.append(file_path)

            test_results = None
            if verification:
                test_results = await self.run_bash(session.session_id, verification)

            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return OpenCodeResult(
                agent_id=agent_id,
                status="completed",
                files_created=created,
                files_modified=modified,
                test_results=test_results,
                duration_ms=duration,
            )

        finally:
            await self.destroy_session(session.session_id)
