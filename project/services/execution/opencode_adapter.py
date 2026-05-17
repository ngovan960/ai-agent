import logging
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.execution.cli_error_ledger import CliErrorLedger
from services.execution.tool_call_limiter import ToolCallLimiter, ToolQuotaExceededError
from services.execution.tool_permission_manager import PermissionDeniedError, ToolPermissionManager

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    operation: str
    path: str
    content: str | None = None
    old_string: str | None = None
    new_string: str | None = None


@dataclass
class OpenCodeResult:
    agent_id: UUID
    status: str
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    test_results: dict | None = None
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0


class OpenCodeAdapter:
    def __init__(
        self,
        project_root: str | None = None,
        agent_role: str = "specialist",
        task_id: UUID | None = None,
        permission_manager: ToolPermissionManager | None = None,
        tool_limiter: ToolCallLimiter | None = None,
        error_ledger: CliErrorLedger | None = None,
    ):
        self.project_root = project_root
        self.agent_role = agent_role
        self.task_id = task_id
        self._permissions = permission_manager or ToolPermissionManager(project_root)
        self._limiter = tool_limiter or ToolCallLimiter()
        self._ledger = error_ledger or CliErrorLedger()

    async def execute(
        self, task_spec: dict, context: dict
    ) -> OpenCodeResult:
        agent_id = uuid4()
        start = datetime.now(UTC)

        try:
            files_to_create = task_spec.get("files_to_create", [])
            files_to_modify = task_spec.get("files_to_modify", [])
            verification = task_spec.get("verification", "")

            created = []
            for file_path in files_to_create:
                try:
                    if self.task_id:
                        self._limiter.check_and_increment(self.task_id, "write", file_path)
                    self._permissions.check_write_permission(self.agent_role, file_path)
                    status = await self.write_file(file_path, "")
                    if status:
                        created.append(file_path)
                except (PermissionDeniedError, ToolQuotaExceededError) as e:
                    logger.error(f"File creation blocked: {file_path} — {e}")
                    return OpenCodeResult(
                        agent_id=agent_id,
                        status="blocked",
                        error=str(e),
                        duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
                    )

            modified = []
            for file_path in files_to_modify:
                try:
                    if self.task_id:
                        self._limiter.check_and_increment(self.task_id, "edit", file_path)
                    self._permissions.check_edit_permission(self.agent_role, file_path)
                    modified.append(file_path)
                except (PermissionDeniedError, ToolQuotaExceededError) as e:
                    logger.error(f"File modification blocked: {file_path} — {e}")
                    return OpenCodeResult(
                        agent_id=agent_id,
                        status="blocked",
                        error=str(e),
                        duration_ms=(datetime.now(UTC) - start).total_seconds() * 1000,
                    )

            test_results = None
            if verification:
                test_results = await self.run_bash(verification)

            duration = (datetime.now(UTC) - start).total_seconds() * 1000

            return OpenCodeResult(
                agent_id=agent_id,
                status="completed",
                files_created=created,
                files_modified=modified,
                test_results=test_results,
                duration_ms=duration,
            )

        except Exception as e:
            logger.exception(f"OpenCode execution failed: {e}")
            return OpenCodeResult(
                agent_id=agent_id,
                status="failed",
                error=str(e),
            )

    async def run_bash(
        self, command: str, timeout: int = 60, file_path: str = ""
    ) -> dict:
        if self.task_id:
            try:
                self._limiter.check_and_increment(self.task_id, "bash", file_path or command)
            except ToolQuotaExceededError as e:
                return {"stdout": "", "stderr": str(e), "exit_code": -1, "success": False}

        try:
            result = subprocess.run(
                shlex.split(command), shell=False, capture_output=True, text=True, timeout=timeout
            )
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

            if result.returncode != 0 and self.task_id:
                self._ledger.record_error(
                    task_id=self.task_id,
                    file_path=file_path or "",
                    command=command,
                    exit_code=result.returncode,
                    error_message=result.stderr,
                )

            return output
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out", "exit_code": -1, "success": False}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1, "success": False}

    async def read_file(self, path: str) -> str | None:
        if self.task_id:
            try:
                self._limiter.check_and_increment(self.task_id, "read", path)
            except ToolQuotaExceededError as e:
                logger.error(f"Read blocked: {path} — {e}")
                return None

        try:
            self._permissions.check_read_permission(self.agent_role, path)
        except PermissionDeniedError as e:
            logger.error(f"Read denied: {path} — {e}")
            return None

        full_path = self._resolve_path(path)
        if os.path.isfile(full_path):
            with open(full_path) as f:
                return f.read()
        return None

    async def write_file(self, path: str, content: str) -> bool:
        full_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return True

    async def edit_file(self, path: str, old_string: str, new_string: str) -> bool:
        content = await self.read_file(path)
        if content is None:
            return False
        if old_string not in content:
            logger.warning(f"edit_file: old_string not found in {path}")
            return False
        updated = content.replace(old_string, new_string)
        if updated == content:
            logger.warning(f"edit_file: no changes made to {path} (identical content)")
            return False
        return await self.write_file(path, updated)

    async def safe_edit_with_retries(
        self, path: str, old_string: str, new_string: str, max_attempts: int = 3
    ) -> bool:
        """Edit file with retry detection. Fails after max_attempts and suggests escalation."""
        for attempt in range(1, max_attempts + 1):
            success = await self.edit_file(path, old_string, new_string)
            if success:
                return True
            if attempt < max_attempts:
                logger.info(f"Edit attempt {attempt}/{max_attempts} failed for {path}, retrying...")
            else:
                logger.error(
                    f"Edit failed after {max_attempts} attempts for {path}. "
                    f"Old string may not match file content due to line drift. "
                    f"Suggestion: re-read the file and try with exact content."
                )
                return False
        return False

    def get_file_warnings(self, file_path: str) -> list[str]:
        """Get historical error warnings for a file."""
        return self._ledger.get_warnings_for_task([file_path])

    def _resolve_path(self, path: str) -> str:
        if self.project_root and not path.startswith("/"):
            return os.path.join(self.project_root, path)
        return path
