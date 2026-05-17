from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.orchestrator.services.workflow_engine import NodeResult, WorkflowEngine, WorkflowResult, WorkflowStatus
from shared.config.state_transitions import is_terminal, validate_transition


class TestWorkflowEngineCore:
    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        mock_db = AsyncMock()
        engine = WorkflowEngine(mock_db)
        assert engine is not None
        assert engine.db == mock_db

    @pytest.mark.asyncio
    async def test_workflow_task_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        engine = WorkflowEngine(mock_db)
        result = await engine.run_workflow(uuid4())
        assert result.status == WorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_node_map_has_all_states(self):
        mock_db = AsyncMock()
        engine = WorkflowEngine(mock_db)
        node_map = {
            "NEW": engine._node_gatekeeper,
            "VALIDATING": engine._node_validator,
            "ANALYZING": engine._node_orchestrator,
            "PLANNING": engine._node_orchestrator,
            "IMPLEMENTING": engine._node_specialist,
            "VERIFYING": engine._node_verification,
            "REVIEWING": engine._node_auditor,
            "ESCALATED": engine._node_mentor,
            "BLOCKED": engine._node_blocked,
        }
        for state, func in node_map.items():
            assert callable(func), f"Node for {state} should be callable"

    @pytest.mark.asyncio
    async def test_gatekeeper_node(self):
        mock_db = AsyncMock()
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.description = "Test task"
        mock_task.title = "Test"
        mock_task.project_id = uuid4()
        mock_task.risk_level = type("S", (), {"value": "LOW"})()
        mock_task.status = type("S", (), {"value": "NEW"})()
        engine = WorkflowEngine(mock_db)
        result = await engine._node_gatekeeper(mock_task)
        assert isinstance(result, NodeResult)

    @pytest.mark.asyncio
    async def test_node_verification_with_low_risk(self):
        mock_db = AsyncMock()
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.risk_level = type("S", (), {"value": "LOW"})()
        mock_task.status = type("S", (), {"value": "VERIFYING"})()
        engine = WorkflowEngine(mock_db)
        result = await engine._node_verification(mock_task)
        assert isinstance(result, NodeResult)

    def test_valid_transition_validates(self):
        valid, _ = validate_transition("NEW", "ANALYZING")
        assert valid

    def test_terminal_state_check(self):
        assert is_terminal("DONE")
        assert is_terminal("FAILED")
        assert is_terminal("CANCELLED")
        assert not is_terminal("NEW")

    @pytest.mark.asyncio
    async def test_cancel_workflow_task_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_engine = WorkflowEngine(mock_db)
        result = await mock_engine.cancel_workflow(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_workflow_success(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.status = type("S", (), {"value": "NEW"})()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_engine = WorkflowEngine(mock_db)
        mock_engine._transition_task = AsyncMock(return_value=True)
        result = await mock_engine.cancel_workflow(mock_task.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_workflow_status(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        task_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        status = await mock_engine.get_workflow_status(task_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        task_id = uuid4()
        
        mock_wf = MagicMock()
        mock_wf.status = "running"
        mock_wf.state = {
            "nodes": [{"node": "gatekeeper", "status": "completed", "error": None}],
            "total_retries": 1,
            "total_cost_usd": 0.05,
            "total_latency_ms": 100
        }
        mock_wf.error = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_wf
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        status = await mock_engine.get_workflow_status(task_id)
        assert status is not None
        assert status["status"] == "running"
        assert status["current_node"] == "gatekeeper"

    @pytest.mark.asyncio
    async def test_resume_workflow_no_saved_state(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await mock_engine.resume_workflow(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_resume_workflow_success(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        mock_result = MagicMock()
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.status = type("S", (), {"value": "ANALYZING"})()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_engine._saved_state[mock_task.id] = {
            "result": WorkflowResult(task_id=mock_task.id, status=WorkflowStatus.RUNNING),
            "current_state": "ANALYZING"
        }
        mock_engine._run_workflow_loop = AsyncMock(return_value=WorkflowResult(task_id=mock_task.id, status=WorkflowStatus.COMPLETED))
        result = await mock_engine.resume_workflow(mock_task.id)
        assert result is not None
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_workflow_status_no_history(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        status = await mock_engine.get_workflow_status(uuid4())
        assert status is None

    @pytest.mark.asyncio
    async def test_workflow_history_no_history(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        history = await mock_engine.get_workflow_history(uuid4())
        assert history is None

    @pytest.mark.asyncio
    async def test_check_existing_task_no_history(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await mock_engine.check_existing_task(uuid4(), "test")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_existing_task_with_history(self):
        mock_db = AsyncMock()
        mock_engine = WorkflowEngine(mock_db)
        task_id = uuid4()
        other_task_id = uuid4()
        
        mock_wf = MagicMock()
        mock_wf.task_id = other_task_id
        mock_wf.state = {
            "nodes": [{"node": "gatekeeper", "output_state": "ANALYZING"}]
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_wf]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await mock_engine.check_existing_task(task_id, "test")
        assert result is not None
        assert result["existing_task_id"] == str(other_task_id)
