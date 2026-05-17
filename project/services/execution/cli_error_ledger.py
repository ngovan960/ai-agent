"""CLI Error Ledger — Security Fix #3

Stores bash command errors from OpenCode tool executions.
When a new task starts, the ledger is scanned for matching files
to warn about historical errors.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class CliErrorRecord:
    task_id: UUID
    file_path: str
    command: str
    exit_code: int
    error_message: str
    error_type: str
    timestamp: str


class CliErrorLedger:
    """3 — CLI Error Ledger for tracking and warning about historical bash errors."""

    def __init__(self):
        self._records: list[CliErrorRecord] = []

    def _detect_error_type(self, error_message: str) -> str:
        """Detect the type of error from the message."""
        error_patterns = {
            "SyntaxError": r"SyntaxError|syntax error|invalid syntax",
            "ImportError": r"ImportError|ModuleNotFoundError|cannot import",
            "AssertionError": r"AssertionError|assert.*failed",
            "TypeError": r"TypeError|type.*error",
            "ValueError": r"ValueError|value.*error",
            "NameError": r"NameError|name.*not defined",
            "AttributeError": r"AttributeError|attribute.*error",
            "KeyError": r"KeyError|key.*error",
            "IndexError": r"IndexError|index.*error",
            "FileNotFoundError": r"FileNotFoundError|No such file",
            "PermissionError": r"PermissionError|permission denied",
            "CompilationError": r"compil|build.*fail|make.*fail",
            "LintError": r"lint|ruff|flake8|pylint|eslint|F\d{3}|E\d{3}|W\d{3}|imported but unused|unused import",
            "TestFailure": r"FAILED|test.*fail|assertion.*fail",
            "TimeoutError": r"timeout|timed out",
        }

        for error_type, pattern in error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return error_type

        return "UnknownError"

    def record_error(
        self,
        task_id: UUID,
        file_path: str,
        command: str,
        exit_code: int,
        error_message: str,
    ) -> CliErrorRecord:
        """Record a CLI error for future reference."""
        error_type = self._detect_error_type(error_message)

        record = CliErrorRecord(
            task_id=task_id,
            file_path=file_path,
            command=command,
            exit_code=exit_code,
            error_message=error_message[:5000],
            error_type=error_type,
            timestamp=datetime.now(UTC).isoformat(),
        )

        self._records.append(record)
        logger.info(
            f"CLI error recorded: {error_type} in {file_path} "
            f"(task={task_id}, exit_code={exit_code})"
        )
        return record

    def check_file_history(self, file_path: str) -> list[CliErrorRecord]:
        """Check if a file has historical errors. Returns matching records."""
        matches = []
        for record in self._records:
            if file_path == record.file_path or record.file_path in file_path or file_path in record.file_path:
                matches.append(record)
        return matches

    def get_warnings_for_task(self, file_paths: list[str]) -> list[str]:
        """Generate warning messages for files with historical errors."""
        warnings = []
        for file_path in file_paths:
            history = self.check_file_history(file_path)
            for record in history:
                warning = (
                    f"⚠️ File '{file_path}' previously failed with {record.error_type} "
                    f"when running: '{record.command}'. "
                    f"Error: {record.error_message[:200]}"
                )
                warnings.append(warning)
        return warnings

    def get_errors_by_type(self, error_type: str) -> list[CliErrorRecord]:
        """Get all errors of a specific type."""
        return [r for r in self._records if r.error_type == error_type]

    def get_recent_errors(self, limit: int = 10) -> list[CliErrorRecord]:
        """Get most recent errors."""
        return self._records[-limit:]

    def get_all_errors(self) -> list[CliErrorRecord]:
        """Get all recorded errors."""
        return list(self._records)

    def clear_errors_for_task(self, task_id: UUID) -> int:
        """Clear errors for a specific task. Returns count cleared."""
        before = len(self._records)
        self._records = [r for r in self._records if r.task_id != task_id]
        cleared = before - len(self._records)
        if cleared > 0:
            logger.info(f"Cleared {cleared} error records for task {task_id}")
        return cleared

    def get_stats(self) -> dict:
        """Get error statistics."""
        type_counts = {}
        for record in self._records:
            type_counts[record.error_type] = type_counts.get(record.error_type, 0) + 1

        return {
            "total_errors": len(self._records),
            "by_type": type_counts,
            "unique_files": len(set(r.file_path for r in self._records)),
            "unique_tasks": len(set(str(r.task_id) for r in self._records)),
        }
