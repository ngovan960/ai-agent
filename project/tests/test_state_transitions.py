import pytest

from shared.config.state_transitions import (
    validate_transition,
    is_terminal,
    get_valid_transitions,
    TERMINAL_STATES,
)


class TestValidateTransition:
    def test_valid_transition_new_to_analyzing(self):
        is_valid, reason = validate_transition("NEW", "ANALYZING")
        assert is_valid is True
        assert "phan loai" in reason.lower() or "condition" in reason.lower()

    def test_valid_transition_analyzing_to_planning(self):
        is_valid, _ = validate_transition("ANALYZING", "PLANNING")
        assert is_valid is True

    def test_valid_transition_planning_to_implementing(self):
        is_valid, _ = validate_transition("PLANNING", "IMPLEMENTING")
        assert is_valid is True

    def test_valid_transition_implementing_to_verifying(self):
        is_valid, _ = validate_transition("IMPLEMENTING", "VERIFYING")
        assert is_valid is True

    def test_valid_transition_verifying_to_reviewing(self):
        is_valid, _ = validate_transition("VERIFYING", "REVIEWING")
        assert is_valid is True

    def test_valid_transition_reviewing_to_done(self):
        is_valid, _ = validate_transition("REVIEWING", "DONE")
        assert is_valid is True

    def test_invalid_transition_done_to_any(self):
        is_valid, _ = validate_transition("DONE", "NEW")
        assert is_valid is False

    def test_invalid_transition_failed_to_any(self):
        is_valid, _ = validate_transition("FAILED", "PLANNING")
        assert is_valid is False

    def test_invalid_transition_cancelled_to_any(self):
        is_valid, _ = validate_transition("CANCELLED", "NEW")
        assert is_valid is False

    def test_invalid_transition_same_status(self):
        is_valid, _ = validate_transition("NEW", "NEW")
        assert is_valid is False

    def test_invalid_transition_skip_workflow(self):
        is_valid, _ = validate_transition("NEW", "DONE")
        assert is_valid is False

    def test_invalid_transition_blocked_to_implementing(self):
        is_valid, _ = validate_transition("BLOCKED", "IMPLEMENTING")
        assert is_valid is False

    def test_unknown_current_status(self):
        is_valid, _ = validate_transition("UNKNOWN", "NEW")
        assert is_valid is False

    def test_unknown_new_status(self):
        is_valid, _ = validate_transition("NEW", "UNKNOWN")
        assert is_valid is False


class TestIsTerminal:
    def test_done_is_terminal(self):
        assert is_terminal("DONE") is True

    def test_failed_is_terminal(self):
        assert is_terminal("FAILED") is True

    def test_cancelled_is_terminal(self):
        assert is_terminal("CANCELLED") is True

    def test_new_is_not_terminal(self):
        assert is_terminal("NEW") is False

    def test_analyzing_is_not_terminal(self):
        assert is_terminal("ANALYZING") is False


class TestGetValidTransitions:
    def test_new_valid_transitions(self):
        transitions = get_valid_transitions("NEW")
        assert "ANALYZING" in transitions
        assert "BLOCKED" in transitions
        assert "VALIDATING" in transitions

    def test_done_no_valid_transitions(self):
        transitions = get_valid_transitions("DONE")
        assert transitions == []

    def test_reviewing_valid_transitions(self):
        transitions = get_valid_transitions("REVIEWING")
        assert "DONE" in transitions
        assert "IMPLEMENTING" in transitions
        assert "ESCALATED" in transitions
        assert "CANCELLED" in transitions

    def test_validating_valid_transitions(self):
        transitions = get_valid_transitions("VALIDATING")
        assert "ANALYZING" in transitions
        assert "NEW" in transitions
        assert "ESCALATED" in transitions
        assert "BLOCKED" in transitions


class TestValidatingState:
    def test_new_to_validating(self):
        is_valid, reason = validate_transition("NEW", "VALIDATING")
        assert is_valid is True

    def test_validating_to_analyzing(self):
        is_valid, _ = validate_transition("VALIDATING", "ANALYZING")
        assert is_valid is True

    def test_validating_to_escalated(self):
        is_valid, _ = validate_transition("VALIDATING", "ESCALATED")
        assert is_valid is True

    def test_validating_to_new(self):
        is_valid, _ = validate_transition("VALIDATING", "NEW")
        assert is_valid is True

    def test_validating_to_blocked(self):
        is_valid, _ = validate_transition("VALIDATING", "BLOCKED")
        assert is_valid is True

    def test_validating_to_done_invalid(self):
        is_valid, _ = validate_transition("VALIDATING", "DONE")
        assert is_valid is False

    def test_validating_is_not_terminal(self):
        assert is_terminal("VALIDATING") is False
