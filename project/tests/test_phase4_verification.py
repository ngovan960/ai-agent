from uuid import uuid4

import pytest

from services.execution.opencode_verification import OpenCodeVerification
from services.orchestrator.services.exit_code_parser import (
    extract_errors,
    parse_exit_code,
    parse_test_results,
)
from services.orchestrator.services.mode_selector import ModeSelector
from services.orchestrator.services.rollback_service import RollbackEngine
from services.orchestrator.services.verification_service import VerificationPipeline
from shared.schemas.verification import (
    RollbackRequest,
    RollbackResponse,
    VerificationRequest,
    VerificationResponse,
)
from shared.schemas.verification import (
    StepResult as StepResultSchema,
)


@pytest.mark.asyncio
class TestModeSelectionWorkflow:
    async def test_low_risk_uses_dev(self):
        selector = ModeSelector()
        assert selector.select("LOW") == "dev"
        assert selector.requires_sandbox("LOW") is False

    async def test_high_risk_uses_prod(self):
        selector = ModeSelector()
        assert selector.select("HIGH") == "prod"
        assert selector.requires_sandbox("HIGH") is True

    async def test_critical_uses_prod(self):
        selector = ModeSelector()
        assert selector.select("CRITICAL") == "prod"
        assert selector.requires_sandbox("CRITICAL") is True


@pytest.mark.asyncio
class TestDevVerificationWorkflow:
    async def test_dev_verification_flow(self, tmp_path):
        (tmp_path / "sample.py").write_text("x = 1")
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path))
        assert result.status in ("verified", "failed")
        assert len(result.steps) == 4
        for step in result.steps:
            assert hasattr(step, "step_name")
            assert hasattr(step, "status")

    async def test_dev_verification_with_errors(self, tmp_path):
        (tmp_path / "broken.py").write_text("import nonexistent_module")
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path))
        assert result.status in ("verified", "failed")


@pytest.mark.asyncio
class TestPipelineWorkflow:
    async def test_pipeline_scoring(self, tmp_path):
        pipeline = VerificationPipeline()
        result = await pipeline.run_pipeline(uuid4(), str(tmp_path), "dev")
        assert 0 <= result.score <= 100
        assert result.status in ("verified", "failed")

    async def test_pipeline_full_flow(self, tmp_path):
        (tmp_path / "hello.py").write_text("print('hello')")
        pipeline = VerificationPipeline()
        result = await pipeline.run_pipeline(uuid4(), str(tmp_path), "dev")
        assert result.duration_ms > 0
        assert len(result.steps) > 0


@pytest.mark.asyncio
class TestExitCodeWorkflow:
    async def test_exit_code_to_status(self):
        assert parse_exit_code(0) == "verified"
        assert parse_exit_code(1) == "failed"

    async def test_error_extraction(self):
        errors = extract_errors("Error: test failure", "", "test")
        assert len(errors) >= 1

    async def test_test_result_parsing(self):
        summary = parse_test_results("= 5 passed, 1 failed =")
        assert summary.passed == 5
        assert summary.failed == 1


@pytest.mark.asyncio
class TestRollbackWorkflow:
    async def test_rollback_trigger(self):
        engine = RollbackEngine()
        record = await engine.trigger_rollback(uuid4(), "Test failure")
        assert record.reason == "Test failure"

    async def test_rollback_audit(self):
        engine = RollbackEngine()
        task_id = uuid4()
        await engine.trigger_rollback(task_id, "Audit test")
        log = engine.get_audit_log()
        assert len(log) > 0

    async def test_disabled_rollback(self):
        engine = RollbackEngine()
        engine.auto_rollback = False
        record = await engine.trigger_rollback(uuid4(), "Disabled")
        assert record.status == "skipped"


@pytest.mark.asyncio
class TestRouterSchemas:
    async def test_verification_request(self):
        req = VerificationRequest(mode="dev")
        assert req.mode == "dev"

    async def test_rollback_request(self):
        req = RollbackRequest(reason="Test rollback")
        assert req.reason == "Test rollback"

    async def test_verification_response(self):
        resp = VerificationResponse(
            task_id=uuid4(),
            status="verified",
            score=85.5,
            steps=[
                StepResultSchema(
                    step_name="lint", status="passed", exit_code=0,
                )
            ],
            errors=[],
            duration_ms=1000.0,
            mode="dev",
        )
        assert resp.status == "verified"
        assert resp.score == 85.5
        assert len(resp.steps) == 1

    async def test_rollback_response(self):
        resp = RollbackResponse(
            task_id=uuid4(),
            status="completed",
            reason="Test",
            rollback_id="rb-123",
            message="Rollback completed",
        )
        assert resp.status == "completed"
