"""Integration tests for Governance Layer (Phase 5.5).

Tests the full governance pipeline: confidence, law engine, cost governor,
and risk classification working together.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.confidence_engine import (
    ConfidenceEngine,
)
from services.orchestrator.services.cost_governor import CostGovernor
from services.orchestrator.services.law_engine import LawEngine
from services.orchestrator.services.risk_classifier import (
    RISK_LEVEL_CRITICAL,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
    RiskClassifier,
)


@pytest.fixture
def laws_yaml_path(tmp_path):
    laws_file = tmp_path / "laws.yaml"
    laws_file.write_text("""
rules:
  - id: LAW-001
    name: No business logic in controller
    severity: high
    description: Controllers must only receive requests.
    check_rule: "no business logic in controllers"
    category: architecture
  - id: LAW-002
    name: All APIs must validate input
    severity: high
    description: Every API must validate input.
    check_rule: "all endpoints must validate"
    category: security
  - id: LAW-005
    name: No hardcoded secrets
    severity: critical
    description: No hardcoded secrets.
    check_rule: "no hardcoded secrets"
    category: security
""")
    return str(laws_file)


@pytest.fixture
def law_engine(laws_yaml_path):
    return LawEngine(laws_path=laws_yaml_path)


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def cost_governor(mock_db):
    return CostGovernor(db_session=mock_db)


@pytest.fixture
def confidence_engine():
    return ConfidenceEngine()


@pytest.fixture
def risk_classifier():
    return RiskClassifier()


class TestConfidenceWithLawCompliance:
    """5.5.1 — Confidence engine integrated with law compliance."""

    def test_high_confidence_with_full_compliance(self, confidence_engine, law_engine):
        task_id = uuid4()
        clean_code = """
from pydantic import BaseModel
class UserCreate(BaseModel):
    name: str
def get_user(req):
    return service.get(req.id)
"""
        compliance = law_engine.check_compliance(clean_code, filename="service.py")
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        result = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 10, "total": 10},
            lint_results={"errors": 0, "warnings": 0, "total_checks": 50},
            retry_count=0,
            max_retries=2,
            law_results=law_results,
        )

        assert result.confidence_score >= 0.8
        assert result.action == "auto_approve"

    def test_low_confidence_with_violations(self, confidence_engine, law_engine):
        task_id = uuid4()
        bad_code = 'API_KEY = "sk-secret123"\ndef post_user(req):\n    data = req.body'
        compliance = law_engine.check_compliance(bad_code, filename="controller.py")
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        result = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 3, "total": 10},
            lint_results={"errors": 10, "warnings": 20, "total_checks": 50},
            retry_count=2,
            max_retries=2,
            law_results=law_results,
        )

        assert result.confidence_score < 0.6

    def test_escalation_threshold(self, confidence_engine, law_engine):
        task_id = uuid4()
        bad_code = 'password = "secret"'
        compliance = law_engine.check_compliance(bad_code)
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        result = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 0, "total": 10},
            lint_results={"errors": 20, "warnings": 30, "total_checks": 50},
            retry_count=2,
            max_retries=2,
            law_results=law_results,
        )

        assert result.action in ("escalate", "takeover_rollback")


class TestLawEngineInAuditor:
    """5.5.2 — Law engine integrated into audit/compliance checks."""

    def test_auditor_detects_violations(self, law_engine):
        code = """
def post_user(request):
    data = request.body
    db.session.query(User).all()
    password = "hardcoded_secret"
"""
        report = law_engine.check_compliance(code, filename="user_controller.py")
        assert not report.is_compliant
        assert report.violated_count >= 1

    def test_auditor_passes_clean_code(self, law_engine):
        code = """
from pydantic import BaseModel
class UserCreate(BaseModel):
    name: str
def get_user(req):
    return service.get(req.id)
"""
        report = law_engine.check_compliance(code, filename="service.py")
        assert report.is_compliant


class TestCostGovernanceWithModelRouter:
    """5.5.3 — Cost governor integrated with model selection."""

    @pytest.mark.asyncio
    async def test_low_cost_task_gets_flash_model(self, cost_governor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        cost_governor._db.execute = AsyncMock(return_value=mock_result)

        governance = await cost_governor.apply_cost_governance(task_complexity="low")
        assert "flash" in governance.recommended_model.lower() or governance.recommended_model in ["deepseek_v4_flash", "minimax_m2_7"]

    @pytest.mark.asyncio
    async def test_high_cost_task_respects_quota(self, cost_governor):
        mock_quota = MagicMock()
        mock_quota.calls_used = 10
        mock_quota.calls_limit = 10
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_quota
        cost_governor._db.execute = AsyncMock(return_value=mock_result)

        governance = await cost_governor.apply_cost_governance(task_complexity="high")
        assert "mentor" not in governance.recommended_model.lower()
        assert governance.within_quota is False


class TestRiskBasedTaskAssignment:
    """5.5.4 — Risk classification integrated with task assignment."""

    def test_low_risk_auto_approve(self, risk_classifier):
        task_id = uuid4()
        classification = risk_classifier.classify(
            task_id=task_id,
            complexity=2,
            data_sensitivity=0,
            user_impact=0,
            deployment_scope=0,
        )
        assert classification.recommended_action == "auto_approve"
        assert classification.workflow_path == "fast_track"

    def test_critical_risk_requires_human(self, risk_classifier):
        task_id = uuid4()
        classification = risk_classifier.classify(
            task_id=task_id,
            complexity=10,
            data_sensitivity=3,
            user_impact=3,
            deployment_scope=2,
        )
        assert classification.recommended_action == "human_approval"
        assert classification.workflow_path == "full_review_human_approval"


class TestRiskBasedModeSelection:
    """5.5.5 — Risk level determines dev vs prod mode."""

    def test_low_risk_dev_mode(self, risk_classifier):
        task_id = uuid4()
        classification = risk_classifier.classify(
            task_id=task_id,
            complexity=1,
            data_sensitivity=0,
            user_impact=0,
            deployment_scope=0,
        )
        assert classification.risk_level == RISK_LEVEL_LOW
        assert classification.workflow_path == "fast_track"

    def test_high_risk_prod_mode(self, risk_classifier):
        task_id = uuid4()
        classification = risk_classifier.classify(
            task_id=task_id,
            complexity=8,
            data_sensitivity=3,
            user_impact=3,
            deployment_scope=2,
        )
        assert classification.risk_level == RISK_LEVEL_CRITICAL
        assert classification.workflow_path == "full_review_human_approval"


class TestGovernanceEndToEnd:
    """5.5.6 — Full governance pipeline end-to-end."""

    def test_full_pipeline_clean_task(self, confidence_engine, law_engine, risk_classifier):
        task_id = uuid4()

        risk = risk_classifier.classify(
            task_id=task_id,
            complexity=3,
            data_sensitivity=0,
            user_impact=1,
            deployment_scope=0,
        )

        clean_code = """
from pydantic import BaseModel
class Input(BaseModel):
    name: str
def get_item(req):
    return service.get(req.id)
"""
        compliance = law_engine.check_compliance(clean_code, filename="service.py")
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        confidence = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 9, "total": 10},
            lint_results={"errors": 0, "warnings": 1, "total_checks": 50},
            retry_count=0,
            max_retries=2,
            law_results=law_results,
        )

        assert risk.risk_level in (RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM)
        assert confidence.confidence_score >= 0.6
        assert compliance.is_compliant

    def test_full_pipeline_risky_task(self, confidence_engine, law_engine, risk_classifier):
        task_id = uuid4()

        risk = risk_classifier.classify(
            task_id=task_id,
            complexity=9,
            data_sensitivity=3,
            user_impact=3,
            deployment_scope=2,
        )

        bad_code = 'SECRET = "abc123"\ndef post_data(req):\n    data = req.body\neval(data)'
        compliance = law_engine.check_compliance(bad_code, filename="controller.py")
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        confidence = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 2, "total": 10},
            lint_results={"errors": 15, "warnings": 20, "total_checks": 50},
            retry_count=2,
            max_retries=2,
            law_results=law_results,
        )

        assert risk.risk_level == RISK_LEVEL_CRITICAL
        assert confidence.confidence_score < 0.6
        assert not compliance.is_compliant

    def test_governance_blocks_bad_task(self, confidence_engine, law_engine, risk_classifier):
        """A task with high risk and low confidence should be blocked."""
        task_id = uuid4()

        risk = risk_classifier.classify(
            task_id=task_id,
            complexity=10,
            data_sensitivity=3,
            user_impact=3,
            deployment_scope=2,
        )

        bad_code = 'password = "secret"\ncursor.execute("DROP TABLE users")'
        compliance = law_engine.check_compliance(bad_code)
        law_results = {
            "total_laws": compliance.total_laws_checked,
            "violated_laws": compliance.violated_count,
        }

        confidence = confidence_engine.calculate(
            task_id=task_id,
            test_results={"passed": 0, "total": 10},
            lint_results={"errors": 30, "warnings": 30, "total_checks": 50},
            retry_count=2,
            max_retries=2,
            law_results=law_results,
        )

        should_block = (
            risk.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL)
            and confidence.confidence_score < 0.6
            and not compliance.is_compliant
        )
        assert should_block is True
