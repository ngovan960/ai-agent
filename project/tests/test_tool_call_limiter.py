"""Tests for Tool-Call Quota Limiter (Security Fix #2)."""

from uuid import uuid4

import pytest

from services.execution.tool_call_limiter import (
    ToolCallLimiter,
    ToolQuotaConfig,
    ToolQuotaExceededError,
)


class TestToolQuotaLimits:
    def setup_method(self):
        self.limiter = ToolCallLimiter()
        self.task_id = uuid4()

    def test_read_within_quota(self):
        for _i in range(5):
            assert self.limiter.check_and_increment(self.task_id, "read", "src/main.py") is True

    def test_read_exceeds_quota(self):
        for _i in range(5):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")

    def test_grep_exceeds_quota(self):
        for _i in range(5):
            self.limiter.check_and_increment(self.task_id, "grep", "pattern")
        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "grep", "pattern")

    def test_glob_exceeds_quota(self):
        for _i in range(3):
            self.limiter.check_and_increment(self.task_id, "glob", "*.py")
        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "glob", "*.py")

    def test_bash_exceeds_quota(self):
        for _i in range(10):
            self.limiter.check_and_increment(self.task_id, "bash", "pytest")
        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "bash", "pytest")

    def test_unknown_tool_allowed(self):
        assert self.limiter.check_and_increment(self.task_id, "unknown_tool", "path") is True


class TestCustomQuota:
    def setup_method(self):
        self.limiter = ToolCallLimiter()
        self.task_id = uuid4()

    def test_custom_read_quota(self):
        self.limiter.set_quota(self.task_id, ToolQuotaConfig(max_read=2))
        self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")

    def test_default_quota_for_other_task(self):
        other_task_id = uuid4()
        self.limiter.set_quota(self.task_id, ToolQuotaConfig(max_read=1))
        for _i in range(5):
            self.limiter.check_and_increment(other_task_id, "read", "src/main.py")


class TestUsageTracking:
    def setup_method(self):
        self.limiter = ToolCallLimiter()
        self.task_id = uuid4()

    def test_get_usage(self):
        self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        self.limiter.check_and_increment(self.task_id, "read", "src/utils.py")
        self.limiter.check_and_increment(self.task_id, "bash", "pytest")

        usage = self.limiter.get_usage(self.task_id)
        assert usage["read"]["used"] == 2
        assert usage["bash"]["used"] == 1
        assert usage["total_calls"] == 3

    def test_get_history(self):
        self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        self.limiter.check_and_increment(self.task_id, "grep", "pattern")

        history = self.limiter.get_history(self.task_id)
        assert len(history) == 2
        assert history[0].tool == "read"
        assert history[1].tool == "grep"


class TestQuotaReset:
    def setup_method(self):
        self.limiter = ToolCallLimiter()
        self.task_id = uuid4()

    def test_reset_allows_more_calls(self):
        for _i in range(5):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")

        with pytest.raises(ToolQuotaExceededError):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")

        self.limiter.reset(self.task_id)
        assert self.limiter.check_and_increment(self.task_id, "read", "src/main.py") is True


class TestQuotaExceededErrorMessage:
    def setup_method(self):
        self.limiter = ToolCallLimiter()
        self.task_id = uuid4()

    def test_error_message_includes_details(self):
        for _i in range(5):
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")

        try:
            self.limiter.check_and_increment(self.task_id, "read", "src/main.py")
        except ToolQuotaExceededError as e:
            assert "read" in str(e).lower()
            assert "5/5" in str(e)
            assert "BLOCKED" in str(e)
