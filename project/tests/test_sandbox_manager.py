from uuid import uuid4

import pytest

from services.execution.sandbox_manager import SandboxManager, SandboxResult


class TestSandboxManager:
    @pytest.mark.asyncio
    async def test_create_manager(self):
        mgr = SandboxManager()
        assert mgr is not None
        assert len(mgr._containers) == 0

    @pytest.mark.asyncio
    async def test_create_sandbox_no_docker(self, tmp_path):
        mgr = SandboxManager()
        result = await mgr.create_sandbox(
            task_id=uuid4(),
            code_path=str(tmp_path),
        )
        assert isinstance(result, SandboxResult)
        assert result.status in ("created", "failed")

    @pytest.mark.asyncio
    async def test_destroy_nonexistent(self):
        mgr = SandboxManager()
        result = await mgr.destroy_container("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_destroy_all_empty(self):
        mgr = SandboxManager()
        count = await mgr.destroy_all()
        assert count == 0

    @pytest.mark.asyncio
    async def test_run_verification_no_container(self):
        mgr = SandboxManager()
        result = await mgr.run_verification("nonexistent")
        assert result.status == "failed"
        assert "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_capture_logs_no_container(self):
        mgr = SandboxManager()
        logs = await mgr.capture_logs("nonexistent")
        assert logs == "No logs available"
