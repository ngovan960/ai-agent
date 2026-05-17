from services.orchestrator.services.mode_selector import (
    ExecutionMode,
    ModeSelector,
    select_mode,
    should_use_prod,
)


class TestModeSelector:
    def test_select_dev_for_low(self):
        assert select_mode("LOW") == ExecutionMode.DEV

    def test_select_dev_for_medium(self):
        assert select_mode("MEDIUM") == ExecutionMode.DEV

    def test_select_prod_for_high(self):
        assert select_mode("HIGH") == ExecutionMode.PROD

    def test_select_prod_for_critical(self):
        assert select_mode("CRITICAL") == ExecutionMode.PROD

    def test_select_prod_for_unknown(self):
        assert select_mode("UNKNOWN") == ExecutionMode.DEV

    def test_should_use_prod_low(self):
        assert should_use_prod("LOW") is False

    def test_should_use_prod_high(self):
        assert should_use_prod("HIGH") is True

    def test_should_use_prod_critical(self):
        assert should_use_prod("CRITICAL") is True

    def test_selector_class(self):
        selector = ModeSelector()
        assert selector.select("LOW") == "dev"
        assert selector.select("HIGH") == "prod"
        assert selector.requires_sandbox("LOW") is False
        assert selector.requires_sandbox("HIGH") is True


class TestHandleVerificationFail:
    def test_proceed_if_verified(self):
        from services.orchestrator.services.mode_selector import handle_verification_fail
        assert handle_verification_fail({"status": "verified", "score": 100}, 0) == "proceed"

    def test_retry_if_failed_below_limit(self):
        from services.orchestrator.services.mode_selector import handle_verification_fail
        assert handle_verification_fail({"status": "failed", "score": 30}, 0) == "retry"

    def test_escalate_if_failed_at_limit(self):
        from services.orchestrator.services.mode_selector import handle_verification_fail
        assert handle_verification_fail({"status": "failed", "score": 30}, 2) == "escalate"
