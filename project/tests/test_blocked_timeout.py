import pytest
from shared.config.state_transitions import (
    get_blocked_timeout_minutes,
    get_blocked_warning_minutes,
    should_send_blocked_warning,
    should_auto_escalate_blocked,
    BLOCKED_TIMEOUT_MINUTES,
    BLOCKED_WARNING_MINUTES,
    STUCK_TASK_TIMEOUT_MINUTES,
    STUCK_TASK_ESCALATION_MINUTES,
)


class TestBlockedTimeoutConstants:
    def test_blocked_timeout_minutes(self):
        assert BLOCKED_TIMEOUT_MINUTES == 120

    def test_blocked_warning_minutes(self):
        assert BLOCKED_WARNING_MINUTES == 60

    def test_stuck_task_timeout_minutes(self):
        assert STUCK_TASK_TIMEOUT_MINUTES == 30

    def test_stuck_task_escalation_minutes(self):
        assert STUCK_TASK_ESCALATION_MINUTES == 60


class TestBlockedTimeoutFunctions:
    def test_get_blocked_timeout_minutes(self):
        assert get_blocked_timeout_minutes() == 120

    def test_get_blocked_warning_minutes(self):
        assert get_blocked_warning_minutes() == 60

    def test_should_send_blocked_warning_below_threshold(self):
        assert should_send_blocked_warning(30) is False

    def test_should_send_blocked_warning_at_threshold(self):
        assert should_send_blocked_warning(60) is True

    def test_should_send_blocked_warning_above_threshold(self):
        assert should_send_blocked_warning(90) is True

    def test_should_auto_escalate_blocked_below_threshold(self):
        assert should_auto_escalate_blocked(60) is False

    def test_should_auto_escalate_blocked_at_threshold(self):
        assert should_auto_escalate_blocked(120) is True

    def test_should_auto_escalate_blocked_above_threshold(self):
        assert should_auto_escalate_blocked(180) is True


class TestStateTransitionsBlockedEscalated:
    def test_blocked_to_escalated_is_valid(self):
        from shared.config.state_transitions import validate_transition

        is_valid, reason = validate_transition("BLOCKED", "ESCALATED")
        assert is_valid is True
        assert "timeout" in reason.lower() or "escalate" in reason.lower()

    def test_blocked_to_planning_is_valid(self):
        from shared.config.state_transitions import validate_transition

        is_valid, _ = validate_transition("BLOCKED", "PLANNING")
        assert is_valid is True

    def test_blocked_to_cancelled_is_valid(self):
        from shared.config.state_transitions import validate_transition

        is_valid, _ = validate_transition("BLOCKED", "CANCELLED")
        assert is_valid is True

    def test_blocked_has_three_exits(self):
        from shared.config.state_transitions import get_valid_transitions

        transitions = get_valid_transitions("BLOCKED")
        assert "PLANNING" in transitions
        assert "CANCELLED" in transitions
        assert "ESCALATED" in transitions
        assert len(transitions) == 3
