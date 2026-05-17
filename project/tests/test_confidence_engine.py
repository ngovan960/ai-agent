"""Tests for Confidence Engine (Phase 5.1)."""

from uuid import uuid4

from services.orchestrator.services.confidence_engine import (
    ConfidenceEngine,
    calculate_confidence,
    calculate_law_compliance,
    calculate_lint_score,
    calculate_retry_penalty,
    calculate_test_pass_rate,
    decide_from_confidence,
)


class TestTestPassRate:
    def test_all_passed(self):
        assert calculate_test_pass_rate({"passed": 10, "total": 10}) == 1.0

    def test_half_passed(self):
        assert calculate_test_pass_rate({"passed": 5, "total": 10}) == 0.5

    def test_none_passed(self):
        assert calculate_test_pass_rate({"passed": 0, "total": 10}) == 0.0

    def test_empty_results(self):
        assert calculate_test_pass_rate({}) == 0.0

    def test_missing_keys(self):
        assert calculate_test_pass_rate({"passed": 3}) == 0.0


class TestLintScore:
    def test_no_issues(self):
        assert calculate_lint_score({"errors": 0, "warnings": 0, "total_checks": 100}) == 1.0

    def test_some_warnings(self):
        result = calculate_lint_score({"errors": 0, "warnings": 10, "total_checks": 100})
        assert result == 0.95

    def test_some_errors(self):
        result = calculate_lint_score({"errors": 5, "warnings": 0, "total_checks": 100})
        assert result == 0.95

    def test_mixed_issues(self):
        result = calculate_lint_score({"errors": 10, "warnings": 10, "total_checks": 100})
        assert result == 0.85

    def test_empty_results(self):
        assert calculate_lint_score({}) == 1.0

    def test_all_fail(self):
        result = calculate_lint_score({"errors": 50, "warnings": 50, "total_checks": 100})
        assert result == 0.25

    def test_clamped_to_zero(self):
        result = calculate_lint_score({"errors": 100, "warnings": 100, "total_checks": 100})
        assert result == 0.0


class TestRetryPenalty:
    def test_no_retries(self):
        assert calculate_retry_penalty(0, 2) == 0.0

    def test_one_retry(self):
        assert calculate_retry_penalty(1, 2) == 0.5

    def test_max_retries(self):
        assert calculate_retry_penalty(2, 2) == 1.0

    def test_zero_max_retries(self):
        assert calculate_retry_penalty(1, 0) == 1.0


class TestLawCompliance:
    def test_full_compliance(self):
        assert calculate_law_compliance({"total_laws": 20, "violated_laws": 0}) == 1.0

    def test_partial_violation(self):
        assert calculate_law_compliance({"total_laws": 20, "violated_laws": 5}) == 0.75

    def test_all_violated(self):
        assert calculate_law_compliance({"total_laws": 20, "violated_laws": 20}) == 0.0

    def test_empty_results(self):
        assert calculate_law_compliance({}) == 1.0


class TestConfidenceFormula:
    def test_perfect_scores(self):
        result = calculate_confidence(
            test_results={"passed": 10, "total": 10},
            lint_results={"errors": 0, "warnings": 0, "total_checks": 100},
            retry_count=0,
            max_retries=2,
            law_results={"total_laws": 20, "violated_laws": 0},
        )
        # Max = 1*0.35 + 1*0.15 - 0*0.20 + 1*0.30 = 0.80
        assert result.confidence_score == 0.80
        assert result.action == "auto_approve"

    def test_zero_scores(self):
        result = calculate_confidence(
            test_results={"passed": 0, "total": 10},
            lint_results={"errors": 100, "warnings": 100, "total_checks": 100},
            retry_count=2,
            max_retries=2,
            law_results={"total_laws": 20, "violated_laws": 20},
        )
        assert result.confidence_score == 0.0
        assert result.action == "takeover_rollback"

    def test_mixed_scores(self):
        result = calculate_confidence(
            test_results={"passed": 7, "total": 10},
            lint_results={"errors": 2, "warnings": 4, "total_checks": 50},
            retry_count=1,
            max_retries=2,
            law_results={"total_laws": 10, "violated_laws": 1},
        )
        t_val = 0.7
        l_val = 0.92
        p_val = 0.5
        a_val = 0.9
        expected = (t_val * 0.35) + (l_val * 0.15) - (p_val * 0.20) + (a_val * 0.30)
        assert abs(result.confidence_score - expected) < 0.001

    def test_default_empty_inputs(self):
        # Empty test_results → T=0, empty lint → L=1.0, no retries → P=0, empty law → A=1.0
        # = 0*0.35 + 1*0.15 - 0*0.20 + 1*0.30 = 0.45
        result = calculate_confidence()
        assert result.confidence_score == 0.45

    def test_clamped_positive(self):
        result = calculate_confidence(
            test_results={"passed": 0, "total": 10},
            lint_results={"errors": 0, "warnings": 0, "total_checks": 100},
            retry_count=0,
            max_retries=2,
            law_results={"total_laws": 20, "violated_laws": 0},
        )
        assert 0 <= result.confidence_score <= 1

    def test_breakdown_values(self):
        result = calculate_confidence(
            test_results={"passed": 7, "total": 10},
            lint_results={"errors": 2, "warnings": 4, "total_checks": 50},
            retry_count=1,
            max_retries=2,
            law_results={"total_laws": 10, "violated_laws": 1},
        )
        assert result.breakdown.test_pass_rate == 0.7
        assert result.breakdown.retry_penalty == 0.5
        assert result.breakdown.law_compliance == 0.9


class TestConfidenceThresholds:
    def test_auto_approve(self):
        assert decide_from_confidence(0.8) == "auto_approve"
        assert decide_from_confidence(0.95) == "auto_approve"
        assert decide_from_confidence(1.0) == "auto_approve"

    def test_require_review(self):
        assert decide_from_confidence(0.6) == "require_review"
        assert decide_from_confidence(0.7) == "require_review"
        assert decide_from_confidence(0.79) == "require_review"

    def test_escalate(self):
        assert decide_from_confidence(0.3) == "escalate"
        assert decide_from_confidence(0.5) == "escalate"
        assert decide_from_confidence(0.59) == "escalate"

    def test_takeover_rollback(self):
        assert decide_from_confidence(0.0) == "takeover_rollback"
        assert decide_from_confidence(0.1) == "takeover_rollback"
        assert decide_from_confidence(0.29) == "takeover_rollback"


class TestConfidenceEngine:
    def test_calculate_and_log(self):
        engine = ConfidenceEngine()
        task_id = uuid4()
        result = engine.calculate(
            task_id=task_id,
            test_results={"passed": 9, "total": 10},
            lint_results={"errors": 1, "warnings": 2, "total_checks": 50},
            retry_count=0,
            max_retries=2,
            law_results={"total_laws": 20, "violated_laws": 1},
        )
        assert 0 <= result.confidence_score <= 1
        assert result.action in ("auto_approve", "require_review", "escalate", "takeover_rollback")

    def test_history_tracking(self):
        engine = ConfidenceEngine()
        task_id = uuid4()
        engine.calculate(task_id=task_id, test_results={"passed": 10, "total": 10})
        engine.calculate(task_id=task_id, test_results={"passed": 5, "total": 10})
        history = engine.get_history(task_id)
        assert len(history) == 2

    def test_history_per_task(self):
        engine = ConfidenceEngine()
        task_id_1 = uuid4()
        task_id_2 = uuid4()
        engine.calculate(task_id=task_id_1, test_results={"passed": 10, "total": 10})
        engine.calculate(task_id=task_id_2, test_results={"passed": 5, "total": 10})
        assert len(engine.get_history(task_id_1)) == 1
        assert len(engine.get_history(task_id_2)) == 1

    def test_all_history(self):
        engine = ConfidenceEngine()
        engine.calculate(task_id=uuid4())
        engine.calculate(task_id=uuid4())
        assert len(engine.get_all_history()) == 2

    def test_history_entry_structure(self):
        engine = ConfidenceEngine()
        task_id = uuid4()
        engine.calculate(task_id=task_id, test_results={"passed": 8, "total": 10})
        history = engine.get_history(task_id)
        entry = history[0]
        assert "task_id" in entry
        assert "confidence_score" in entry
        assert "test_pass_rate" in entry
        assert "lint_score" in entry
        assert "retry_penalty" in entry
        assert "law_compliance" in entry
        assert "action" in entry
        assert "calculated_at" in entry
