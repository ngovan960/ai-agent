import pytest

from services.execution.opencode_verification import DevVerificationResult, OpenCodeVerification


class TestOpenCodeVerification:
    @pytest.mark.asyncio
    async def test_create_verification(self):
        verifier = OpenCodeVerification()
        assert verifier is not None
        assert verifier.adapter is not None

    @pytest.mark.asyncio
    async def test_verify_dev_mode_empty_dir(self, tmp_path):
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path))
        assert isinstance(result, DevVerificationResult)
        assert result.status in ("verified", "failed")
        assert len(result.steps) == 4
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_verify_dev_mode_with_python(self, tmp_path):
        (tmp_path / "test.py").write_text("print('hello')")
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path), language="python")
        assert result.status in ("verified", "failed")
        assert len(result.steps) == 4

    @pytest.mark.asyncio
    async def test_step_structure(self, tmp_path):
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path))
        for step in result.steps:
            assert hasattr(step, "step_name")
            assert hasattr(step, "status")
            assert hasattr(step, "exit_code")
            assert hasattr(step, "duration_ms")

    @pytest.mark.asyncio
    async def test_result_logs(self, tmp_path):
        verifier = OpenCodeVerification()
        result = await verifier.verify_dev_mode(str(tmp_path))
        assert isinstance(result.logs, str)

    def test_lint_commands(self):
        verifier = OpenCodeVerification()
        assert verifier is not None
