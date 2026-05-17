"""Tool-Call Quota Limiter — Security Fix #2

Limits the number of tool calls per task to prevent context bloating and runaway costs.
Each task has a quota for each tool type. Exceeding quota raises ToolQuotaExceededError
and the task is marked BLOCKED.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class ToolQuotaExceededError(Exception):
    """Raised when an agent exceeds its tool-call quota."""
    pass


@dataclass
class ToolQuotaConfig:
    max_read: int = 5
    max_grep: int = 5
    max_glob: int = 3
    max_bash: int = 10
    max_write: int = 50
    max_edit: int = 20


@dataclass
class ToolCallRecord:
    tool: str
    path: str
    timestamp: str


@dataclass
class ToolCallState:
    task_id: UUID
    read_count: int = 0
    grep_count: int = 0
    glob_count: int = 0
    bash_count: int = 0
    write_count: int = 0
    edit_count: int = 0
    history: list[ToolCallRecord] = field(default_factory=list)


TOOL_COUNT_MAP = {
    "read": ("read_count", "max_read"),
    "grep": ("grep_count", "max_grep"),
    "glob": ("glob_count", "max_glob"),
    "bash": ("bash_count", "max_bash"),
    "write": ("write_count", "max_write"),
    "edit": ("edit_count", "max_edit"),
}


class ToolCallLimiter:
    """2 — Tool-call quota limiter per task."""

    def __init__(self, default_quota: ToolQuotaConfig | None = None):
        self._default_quota = default_quota or ToolQuotaConfig()
        self._states: dict[str, ToolCallState] = {}
        self._quotas: dict[str, ToolQuotaConfig] = {}

    def set_quota(self, task_id: UUID, quota: ToolQuotaConfig) -> None:
        """Set custom quota for a specific task."""
        self._quotas[str(task_id)] = quota

    def get_quota(self, task_id: UUID) -> ToolQuotaConfig:
        """Get quota for a task (custom or default)."""
        return self._quotas.get(str(task_id), self._default_quota)

    def _get_state(self, task_id: UUID) -> ToolCallState:
        """Get or create tool call state for a task."""
        key = str(task_id)
        if key not in self._states:
            self._states[key] = ToolCallState(task_id=task_id)
        return self._states[key]

    def check_and_increment(self, task_id: UUID, tool: str, path: str = "") -> bool:
        """Check quota and increment counter. Raises ToolQuotaExceededError if exceeded."""
        state = self._get_state(task_id)
        quota = self.get_quota(task_id)
        mapping = TOOL_COUNT_MAP.get(tool)

        if not mapping:
            logger.warning(f"Unknown tool type: {tool}, allowing call")
            return True

        count_attr, max_attr = mapping
        current_count = getattr(state, count_attr)
        max_allowed = getattr(quota, max_attr)

        if current_count >= max_allowed:
            raise ToolQuotaExceededError(
                f"Task {task_id} exceeded {tool} quota: "
                f"{current_count}/{max_allowed} calls used. "
                f"Task will be marked BLOCKED."
            )

        setattr(state, count_attr, current_count + 1)
        state.history.append(ToolCallRecord(
            tool=tool,
            path=path,
            timestamp=datetime.now(UTC).isoformat(),
        ))

        return True

    def get_usage(self, task_id: UUID) -> dict:
        """Get current tool usage for a task."""
        state = self._get_state(task_id)
        quota = self.get_quota(task_id)
        return {
            "task_id": str(task_id),
            "read": {"used": state.read_count, "limit": quota.max_read},
            "grep": {"used": state.grep_count, "limit": quota.max_grep},
            "glob": {"used": state.glob_count, "limit": quota.max_glob},
            "bash": {"used": state.bash_count, "limit": quota.max_bash},
            "write": {"used": state.write_count, "limit": quota.max_write},
            "edit": {"used": state.edit_count, "limit": quota.max_edit},
            "total_calls": len(state.history),
        }

    def reset(self, task_id: UUID) -> None:
        """Reset tool call counters for a task (e.g., on retry)."""
        key = str(task_id)
        if key in self._states:
            state = self._states[key]
            self._states[key] = ToolCallState(task_id=state.task_id)
            logger.info(f"Tool call quota reset for task {task_id}")

    def get_history(self, task_id: UUID) -> list[ToolCallRecord]:
        """Get tool call history for a task."""
        state = self._get_state(task_id)
        return list(state.history)
