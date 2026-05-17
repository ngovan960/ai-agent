"""Tests for Risk Classification (Phase 5.4)."""

from uuid import uuid4

from services.orchestrator.services.risk_classifier import (
    ACTION_AUTO_APPROVE,
    ACTION_HUMAN_APPROVAL,
    ACTION_REQUIRE_AUDIT,
    ACTION_SENIOR_REVIEW,
    PATH_FAST_TRACK,
    PATH_FULL_REVIEW,
    PATH_REVIEW_GATE,
    PATH_STANDARD,
    RISK_LEVEL_CRITICAL,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
    RiskClassifier,
    calculate_risk_score,
    classify_risk,
    get_risk_action,
    route_by_risk,
)


class TestRiskScoring:
    def test_minimum_score(self):
        score = calculate_risk_score(complexity=1, data_sensitivity=0, user_impact=0, deployment_scope=0)
        assert score == 1.0

    def test_maximum_score(self):
        score = calculate_risk_score(complexity=10, data_sensitivity=3, user_impact=3, deployment_scope=2)
        assert score == 10.0

    def test_default_values(self):
        score = calculate_risk_score()
        assert score == 2.5

    def test_medium_complexity(self):
        score = calculate_risk_score(complexity=5)
        assert score == 2.5

    def test_high_data_sensitivity(self):
        score = calculate_risk_score(complexity=1, data_sensitivity=3)
        assert score == 3.5

    def test_clamped_minimum(self):
        score = calculate_risk_score(complexity=0, data_sensitivity=0, user_impact=0, deployment_scope=0)
        assert score == 1.0

    def test_clamped_maximum(self):
        score = calculate_risk_score(complexity=20, data_sensitivity=10, user_impact=10, deployment_scope=10)
        assert score == 10.0


class TestRiskLevels:
    def test_low(self):
        assert classify_risk(1.0) == RISK_LEVEL_LOW
        assert classify_risk(3.0) == RISK_LEVEL_LOW

    def test_medium(self):
        assert classify_risk(3.1) == RISK_LEVEL_MEDIUM
        assert classify_risk(6.0) == RISK_LEVEL_MEDIUM

    def test_high(self):
        assert classify_risk(6.1) == RISK_LEVEL_HIGH
        assert classify_risk(8.0) == RISK_LEVEL_HIGH

    def test_critical(self):
        assert classify_risk(8.1) == RISK_LEVEL_CRITICAL
        assert classify_risk(10.0) == RISK_LEVEL_CRITICAL


class TestRiskActions:
    def test_low_action(self):
        assert get_risk_action(RISK_LEVEL_LOW) == ACTION_AUTO_APPROVE

    def test_medium_action(self):
        assert get_risk_action(RISK_LEVEL_MEDIUM) == ACTION_REQUIRE_AUDIT

    def test_high_action(self):
        assert get_risk_action(RISK_LEVEL_HIGH) == ACTION_SENIOR_REVIEW

    def test_critical_action(self):
        assert get_risk_action(RISK_LEVEL_CRITICAL) == ACTION_HUMAN_APPROVAL

    def test_unknown_action(self):
        assert get_risk_action("UNKNOWN") == ACTION_REQUIRE_AUDIT


class TestWorkflowRouting:
    def test_low_routing(self):
        assert route_by_risk(RISK_LEVEL_LOW) == PATH_FAST_TRACK

    def test_medium_routing(self):
        assert route_by_risk(RISK_LEVEL_MEDIUM) == PATH_STANDARD

    def test_high_routing(self):
        assert route_by_risk(RISK_LEVEL_HIGH) == PATH_REVIEW_GATE

    def test_critical_routing(self):
        assert route_by_risk(RISK_LEVEL_CRITICAL) == PATH_FULL_REVIEW

    def test_unknown_routing(self):
        assert route_by_risk("UNKNOWN") == PATH_STANDARD


class TestRiskClassifier:
    def test_classify_low_risk(self):
        classifier = RiskClassifier()
        task_id = uuid4()
        result = classifier.classify(
            task_id=task_id,
            complexity=2,
            data_sensitivity=0,
            user_impact=0,
            deployment_scope=0,
        )
        assert result.risk_level == RISK_LEVEL_LOW
        assert result.recommended_action == ACTION_AUTO_APPROVE
        assert result.workflow_path == PATH_FAST_TRACK

    def test_classify_medium_risk(self):
        classifier = RiskClassifier()
        task_id = uuid4()
        result = classifier.classify(
            task_id=task_id,
            complexity=5,
            data_sensitivity=1,
            user_impact=1,
            deployment_scope=0,
        )
        assert result.risk_level == RISK_LEVEL_MEDIUM
        assert result.recommended_action == ACTION_REQUIRE_AUDIT
        assert result.workflow_path == PATH_STANDARD

    def test_classify_high_risk(self):
        classifier = RiskClassifier()
        task_id = uuid4()
        result = classifier.classify(
            task_id=task_id,
            complexity=6,
            data_sensitivity=1,
            user_impact=1,
            deployment_scope=1,
        )
        assert result.risk_level == RISK_LEVEL_HIGH
        assert result.recommended_action == ACTION_SENIOR_REVIEW
        assert result.workflow_path == PATH_REVIEW_GATE

    def test_classify_critical_risk(self):
        classifier = RiskClassifier()
        task_id = uuid4()
        result = classifier.classify(
            task_id=task_id,
            complexity=10,
            data_sensitivity=3,
            user_impact=3,
            deployment_scope=2,
        )
        assert result.risk_level == RISK_LEVEL_CRITICAL
        assert result.recommended_action == ACTION_HUMAN_APPROVAL
        assert result.workflow_path == PATH_FULL_REVIEW

    def test_to_response(self):
        classifier = RiskClassifier()
        task_id = uuid4()
        classification = classifier.classify(task_id=task_id)
        response = classifier.to_response(task_id, classification)
        assert response.task_id == task_id
        assert response.risk_score == classification.risk_score
        assert response.risk_level == classification.risk_level
        assert response.factors == classification.factors
