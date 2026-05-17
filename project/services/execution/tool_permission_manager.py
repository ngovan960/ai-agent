"""Role-based Tool Permission Manager — Security Fix #4

Enforces file access permissions per agent role:
- specialist: write/edit /src, /services only; read /tests only
- tester: write/edit /tests only; read /src only
- auditor: read everywhere; write nowhere
- gatekeeper: read everywhere; write config only
- orchestrator: read everywhere; write config only
- mentor: read everywhere; write config only
- devops: write/edit /deploy, /scripts only; read everywhere

Path violations raise PermissionDeniedError and log to audit.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PermissionDeniedError(Exception):
    """Raised when an agent attempts an unauthorized file operation."""
    pass


@dataclass
class PermissionRule:
    role: str
    allowed_dirs_write: list[str]
    allowed_dirs_read: list[str]
    allowed_dirs_edit: list[str]
    denied_patterns: list[str]


ROLE_PERMISSIONS: dict[str, PermissionRule] = {
    "specialist": PermissionRule(
        role="specialist",
        allowed_dirs_write=["src", "services", "lib", "app"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "test", "shared"],
        allowed_dirs_edit=["src", "services", "lib", "app"],
        denied_patterns=[".env", "laws.yaml", "models.yaml"],
    ),
    "tester": PermissionRule(
        role="tester",
        allowed_dirs_write=["tests", "test"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "test", "shared"],
        allowed_dirs_edit=["tests", "test"],
        denied_patterns=[".env", "laws.yaml", "models.yaml"],
    ),
    "auditor": PermissionRule(
        role="auditor",
        allowed_dirs_write=[],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "shared", "governance"],
        allowed_dirs_edit=[],
        denied_patterns=[".env", "models.yaml"],
    ),
    "gatekeeper": PermissionRule(
        role="gatekeeper",
        allowed_dirs_write=["config", "shared/config"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "shared", "governance"],
        allowed_dirs_edit=["config", "shared/config"],
        denied_patterns=[".env", "laws.yaml"],
    ),
    "orchestrator": PermissionRule(
        role="orchestrator",
        allowed_dirs_write=["config", "shared/config"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "shared", "governance"],
        allowed_dirs_edit=["config", "shared/config"],
        denied_patterns=[".env", "laws.yaml"],
    ),
    "mentor": PermissionRule(
        role="mentor",
        allowed_dirs_write=["config", "shared/config"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "shared", "governance"],
        allowed_dirs_edit=["config", "shared/config"],
        denied_patterns=[".env", "laws.yaml"],
    ),
    "devops": PermissionRule(
        role="devops",
        allowed_dirs_write=["deploy", "scripts", "docker", "ci"],
        allowed_dirs_read=["src", "services", "lib", "app", "tests", "shared", "deploy", "scripts"],
        allowed_dirs_edit=["deploy", "scripts", "docker", "ci"],
        denied_patterns=[".env", "laws.yaml", "models.yaml"],
    ),
}


class ToolPermissionManager:
    """4 — Role-based tool permission enforcement."""

    def __init__(self, project_root: str | None = None):
        self._project_root = project_root or ""

    def check_write_permission(self, agent_role: str, file_path: str) -> bool:
        """Check if agent role can write to file_path."""
        rule = ROLE_PERMISSIONS.get(agent_role)
        if not rule:
            logger.warning(f"Unknown agent role: {agent_role}, denying write")
            return False

        for pattern in rule.denied_patterns:
            if pattern in file_path:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied write to '{file_path}': "
                    f"matches denied pattern '{pattern}'"
                )

        normalized = file_path.replace("\\", "/")
        if normalized.startswith("/"):
            if self._project_root and normalized.startswith(self._project_root):
                normalized = normalized[len(self._project_root):].lstrip("/")
            else:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied write to '{file_path}': "
                    f"absolute path outside project root"
                )

        for allowed_dir in rule.allowed_dirs_write:
            if normalized.startswith(allowed_dir + "/") or normalized.startswith(allowed_dir):
                return True

        raise PermissionDeniedError(
            f"Role '{agent_role}' denied write to '{file_path}': "
            f"not in allowed dirs {rule.allowed_dirs_write}"
        )

    def check_read_permission(self, agent_role: str, file_path: str) -> bool:
        """Check if agent role can read file_path."""
        rule = ROLE_PERMISSIONS.get(agent_role)
        if not rule:
            logger.warning(f"Unknown agent role: {agent_role}, denying read")
            return False

        for pattern in rule.denied_patterns:
            if pattern in file_path:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied read from '{file_path}': "
                    f"matches denied pattern '{pattern}'"
                )

        normalized = file_path.replace("\\", "/")
        if normalized.startswith("/"):
            if self._project_root and normalized.startswith(self._project_root):
                normalized = normalized[len(self._project_root):].lstrip("/")
            else:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied read from '{file_path}': "
                    f"absolute path outside project root"
                )

        for allowed_dir in rule.allowed_dirs_read:
            if normalized.startswith(allowed_dir + "/") or normalized.startswith(allowed_dir):
                return True

        raise PermissionDeniedError(
            f"Role '{agent_role}' denied read from '{file_path}': "
            f"not in allowed dirs {rule.allowed_dirs_read}"
        )

    def check_edit_permission(self, agent_role: str, file_path: str) -> bool:
        """Check if agent role can edit file_path."""
        rule = ROLE_PERMISSIONS.get(agent_role)
        if not rule:
            logger.warning(f"Unknown agent role: {agent_role}, denying edit")
            return False

        for pattern in rule.denied_patterns:
            if pattern in file_path:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied edit to '{file_path}': "
                    f"matches denied pattern '{pattern}'"
                )

        normalized = file_path.replace("\\", "/")
        if normalized.startswith("/"):
            if self._project_root and normalized.startswith(self._project_root):
                normalized = normalized[len(self._project_root):].lstrip("/")
            else:
                raise PermissionDeniedError(
                    f"Role '{agent_role}' denied edit to '{file_path}': "
                    f"absolute path outside project root"
                )

        for allowed_dir in rule.allowed_dirs_edit:
            if normalized.startswith(allowed_dir + "/") or normalized.startswith(allowed_dir):
                return True

        raise PermissionDeniedError(
            f"Role '{agent_role}' denied edit to '{file_path}': "
            f"not in allowed dirs {rule.allowed_dirs_edit}"
        )

    def get_role_permissions(self, agent_role: str) -> dict | None:
        """Get permission summary for a role."""
        rule = ROLE_PERMISSIONS.get(agent_role)
        if not rule:
            return None
        return {
            "role": rule.role,
            "can_write": rule.allowed_dirs_write,
            "can_read": rule.allowed_dirs_read,
            "can_edit": rule.allowed_dirs_edit,
            "denied_patterns": rule.denied_patterns,
        }
