import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from shared.models.task import Task, TaskStatus, TaskPriority
from shared.config.state_transitions import validate_transition
from services.orchestrator.services.workflow_engine import (
    WorkflowEngine,
    WorkflowStatus,
    NodeResult,
    WorkflowResult,
    MAX_WORKFLOW_RETRIES,
)
from services.orchestrator.services.agent_dispatcher import AgentDispatchResult


class TestWorkflowEngineNodes:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def mock_dispatcher(self):
        disp = MagicMock()
        disp.dispatch_gatekeeper = AsyncMock()
        disp.dispatch_orchestrator = AsyncMock()
        disp.dispatch_specialist = AsyncMock()
        disp.dispatch_auditor = AsyncMock()
        disp.dispatch_mentor = AsyncMock()
        disp.dispatch = AsyncMock()
        return disp

    @pytest.fixture
    def engine(self, mock_db, mock_dispatcher):
        return WorkflowEngine(db=mock_db, agent_dispatcher=mock_dispatcher)

    @pytest.fixture
    def mock_task(self):
        task = MagicMock(spec=Task)
        task.id = uuid4()
        task.project_id = uuid4()
        task.title = "Test Task"
        task.description = "Test description"
        task.expected_output = "Expected output"
        task.priority = MagicMock()
        task.priority.value = "MEDIUM"
        task.status = MagicMock()
        task.status.value = "NEW"
        task.retries = 0
        task.failure_reason = None
        return task

    async def test_node_gatekeeper_success(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_gatekeeper.return_value = AgentDispatchResult(
            agent_name="gatekeeper",
            model_used="deepseek_v4_flash",
            content='{"intent": "add_feature", "complexity_score": 5}',
            parsed_output={"intent": "add_feature"},
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.0001,
            latency_ms=300,
            status="completed",
        )
        result = await engine._node_gatekeeper(mock_task)
        assert result.status == "completed"
        assert result.output_state == "ANALYZING"

    async def test_node_gatekeeper_failure(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_gatekeeper.side_effect = Exception("API error")
        result = await engine._node_gatekeeper(mock_task)
        assert result.status == "failed"

    async def test_node_orchestrator(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_orchestrator.return_value = AgentDispatchResult(
            agent_name="orchestrator",
            model_used="qwen_3_6_plus",
            content='{"workflow_plan": {"execution_order": []}}',
            parsed_output={},
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.001,
            latency_ms=400,
            status="completed",
        )
        result = await engine._node_orchestrator(mock_task)
        assert result.status == "completed"
        assert result.output_state == "PLANNING"

    async def test_node_specialist(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_specialist.return_value = AgentDispatchResult(
            agent_name="specialist",
            model_used="deepseek_v4_pro",
            content="FILE: app.py\n```python\ndef hello(): pass\n```",
            parsed_output=None,
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.002,
            latency_ms=800,
            status="completed",
        )
        result = await engine._node_specialist(mock_task)
        assert result.status == "completed"
        assert result.output_state == "VERIFYING"

    async def test_node_verification(self, engine, mock_task):
        result = await engine._node_verification(mock_task)
        assert result.status == "completed"
        assert result.output_state == "REVIEWING"

    async def test_node_auditor_approve(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_auditor.return_value = AgentDispatchResult(
            agent_name="auditor",
            model_used="qwen_3_5_plus",
            content='{"verdict": "APPROVED", "scores": {"overall": 0.85}}',
            parsed_output={"verdict": "APPROVED", "scores": {"overall": 0.85}},
            input_tokens=1500,
            output_tokens=300,
            cost_usd=0.001,
            latency_ms=500,
            status="completed",
        )
        result = await engine._node_auditor(mock_task)
        assert result.status == "completed"
        assert result.output_state == "DONE"

    async def test_node_auditor_revise(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_auditor.return_value = AgentDispatchResult(
            agent_name="auditor",
            model_used="qwen_3_5_plus",
            content='{"verdict": "REVISE"}',
            parsed_output={"verdict": "REVISE"},
            input_tokens=1000,
            output_tokens=200,
            cost_usd=0.001,
            latency_ms=400,
            status="completed",
        )
        result = await engine._node_auditor(mock_task)
        assert result.output_state == "IMPLEMENTING"

    async def test_node_auditor_escalate(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_auditor.return_value = AgentDispatchResult(
            agent_name="auditor",
            model_used="qwen_3_5_plus",
            content='{"verdict": "ESCALATE"}',
            parsed_output={"verdict": "ESCALATE"},
            input_tokens=1000,
            output_tokens=200,
            cost_usd=0.001,
            latency_ms=400,
            status="completed",
        )
        result = await engine._node_auditor(mock_task)
        assert result.output_state == "ESCALATED"

    async def test_node_mentor_reject(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_mentor.return_value = AgentDispatchResult(
            agent_name="mentor",
            model_used="qwen_3_6_plus",
            content='{"verdict": "REJECT", "reason": "infeasible"}',
            parsed_output={"verdict": "REJECT"},
            input_tokens=2000,
            output_tokens=400,
            cost_usd=0.002,
            latency_ms=600,
            status="completed",
        )
        result = await engine._node_mentor(mock_task)
        assert result.output_state == "FAILED"

    async def test_node_mentor_modify(self, engine, mock_dispatcher, mock_task):
        mock_dispatcher.dispatch_mentor.return_value = AgentDispatchResult(
            agent_name="mentor",
            model_used="qwen_3_6_plus",
            content='{"verdict": "MODIFY", "resolution_plan": []}',
            parsed_output={"verdict": "MODIFY"},
            input_tokens=2000,
            output_tokens=400,
            cost_usd=0.002,
            latency_ms=600,
            status="completed",
        )
        result = await engine._node_mentor(mock_task)
        assert result.output_state == "PLANNING"

    async def test_node_blocked(self, engine, mock_task):
        result = await engine._node_blocked(mock_task)
        assert result.output_state == "ESCALATED"

    @patch("services.orchestrator.services.workflow_engine.task_service")
    async def test_run_workflow_run_state_machine(self, mock_ts, engine, mock_db, mock_task):
        mock_ts.get_task = AsyncMock(return_value=mock_task)
        mock_ts.transition_task_state = AsyncMock(return_value=(mock_task, None))

        mock_task.status.value = "NEW"
        engine._node_gatekeeper = AsyncMock(return_value=NodeResult(
            node_name="gatekeeper", status="completed",
            input_state="NEW", output_state="ANALYZING", agent_result=None,
        ))
        engine._run_node = AsyncMock(side_effect=[
            NodeResult(node_name="gatekeeper", status="completed", input_state="NEW", output_state="ANALYZING", agent_result=None),
            NodeResult(node_name="orchestrator", status="completed", input_state="ANALYZING", output_state="PLANNING", agent_result=None),
        ])

        result = await engine.run_workflow(mock_task.id)
        assert result is not None

    @patch("services.orchestrator.services.workflow_engine.task_service")
    async def test_run_workflow_task_not_found(self, mock_ts, engine):
        mock_ts.get_task = AsyncMock(return_value=None)
        result = await engine.run_workflow(uuid4())
        assert result.status == WorkflowStatus.FAILED
        assert "not found" in result.error.lower()

    @patch("services.orchestrator.services.workflow_engine.task_service")
    async def test_cancel_workflow(self, mock_ts, engine, mock_task):
        mock_ts.get_task = AsyncMock(return_value=mock_task)
        mock_ts.transition_task_state = AsyncMock(return_value=(mock_task, None))
        mock_task.status.value = "IMPLEMENTING"
        result = await engine.cancel_workflow(mock_task.id)
        assert result is True

    @patch("services.orchestrator.services.workflow_engine.task_service")
    async def test_cancel_workflow_terminal_state(self, mock_ts, engine, mock_task):
        mock_ts.get_task = AsyncMock(return_value=mock_task)
        mock_task.status.value = "DONE"
        result = await engine.cancel_workflow(mock_task.id)
        assert result is False


class TestWorkflowResultModel:
    def test_workflow_result_defaults(self):
        tid = uuid4()
        result = WorkflowResult(task_id=tid, status=WorkflowStatus.PENDING)
        assert result.task_id == tid
        assert result.nodes == []
        assert result.total_cost_usd == 0.0

    def test_node_result_model(self):
        nr = NodeResult(
            node_name="gatekeeper",
            status="completed",
            input_state="NEW",
            output_state="ANALYZING",
            agent_result=None,
        )
        assert nr.node_name == "gatekeeper"
        assert nr.retry_count == 0


class TestWorkflowStateTransitions:
    def test_new_to_analyzing(self):
        is_valid, reason = validate_transition("NEW", "ANALYZING")
        assert is_valid

    def test_reviewing_to_done(self):
        is_valid, reason = validate_transition("REVIEWING", "DONE")
        assert is_valid

    def test_reviewing_to_implementing(self):
        is_valid, reason = validate_transition("REVIEWING", "IMPLEMENTING")
        assert is_valid

    def test_reviewing_to_escalated(self):
        is_valid, reason = validate_transition("REVIEWING", "ESCALATED")
        assert is_valid

    def test_escalated_to_done_needs_verified_output(self):
        is_valid, reason = validate_transition("ESCALATED", "DONE", has_verified_output=False)
        assert not is_valid
        is_valid2, _ = validate_transition("ESCALATED", "DONE", has_verified_output=True)
        assert is_valid2

    def test_escalated_to_planning(self):
        is_valid, reason = validate_transition("ESCALATED", "PLANNING")
        assert is_valid

    def test_escalated_to_failed(self):
        is_valid, reason = validate_transition("ESCALATED", "FAILED")
        assert is_valid

    def test_all_workflow_node_transitions_valid(self):
        transitions = [
            ("NEW", "ANALYZING"),
            ("ANALYZING", "PLANNING"),
            ("PLANNING", "IMPLEMENTING"),
            ("IMPLEMENTING", "VERIFYING"),
            ("VERIFYING", "REVIEWING"),
            ("REVIEWING", "DONE"),
            ("REVIEWING", "IMPLEMENTING"),
            ("REVIEWING", "ESCALATED"),
        ]
        for current, target in transitions:
            is_valid, reason = validate_transition(current, target)
            assert is_valid, f"Transition {current} → {target} should be valid, got: {reason}"
