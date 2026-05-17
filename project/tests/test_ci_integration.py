from uuid import uuid4

import pytest

from services.orchestrator.services.ci_integration import CIIntegrationService, CIRun


class TestCIIntegration:
    @pytest.mark.asyncio
    async def test_create_service(self):
        svc = CIIntegrationService()
        assert svc is not None
        assert len(svc._runs) == 0

    @pytest.mark.asyncio
    async def test_trigger_ci_returns_pipeline_id(self):
        svc = CIIntegrationService()
        pipeline_id = await svc.trigger_ci(uuid4())
        assert pipeline_id is not None
        assert len(pipeline_id) > 0

    @pytest.mark.asyncio
    async def test_trigger_ci_creates_run(self):
        svc = CIIntegrationService()
        task_id = uuid4()
        pipeline_id = await svc.trigger_ci(task_id)
        run = await svc.get_ci_status(pipeline_id)
        assert run is not None
        assert run.task_id == task_id
        assert run.status in ("pending", "simulated", "triggered")

    @pytest.mark.asyncio
    async def test_ci_status_tracking(self):
        svc = CIIntegrationService()
        pipeline_id = await svc.trigger_ci(uuid4())
        run = await svc.get_ci_status(pipeline_id)
        assert isinstance(run, CIRun)
        assert run.pipeline_id == pipeline_id

    @pytest.mark.asyncio
    async def test_handle_callback_unknown(self):
        svc = CIIntegrationService()
        result = await svc.handle_ci_callback("nonexistent", {"status": "failed"})
        assert result == "unknown"

    @pytest.mark.asyncio
    async def test_handle_callback_passed(self):
        svc = CIIntegrationService()
        pipeline_id = await svc.trigger_ci(uuid4())
        result = await svc.handle_ci_callback(pipeline_id, {"status": "passed"})
        assert result == "verified"
        run = await svc.get_ci_status(pipeline_id)
        assert run.status == "passed"
        assert run.completed_at is not None

    @pytest.mark.asyncio
    async def test_handle_callback_failed(self):
        svc = CIIntegrationService()
        pipeline_id = await svc.trigger_ci(uuid4())
        result = await svc.handle_ci_callback(pipeline_id, {"status": "failed"})
        assert result == "failed"

    @pytest.mark.asyncio
    async def test_get_ci_status_nonexistent(self):
        svc = CIIntegrationService()
        run = await svc.get_ci_status("nonexistent")
        assert run is None

    @pytest.mark.asyncio
    async def test_multiple_runs(self):
        svc = CIIntegrationService()
        id1 = await svc.trigger_ci(uuid4())
        id2 = await svc.trigger_ci(uuid4())
        assert id1 != id2
        run1 = await svc.get_ci_status(id1)
        run2 = await svc.get_ci_status(id2)
        assert run1.pipeline_id != run2.pipeline_id
