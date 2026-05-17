import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services import tasks as task_service
from services.orchestrator.services import validation as validation_service
from services.orchestrator.services.agent_dispatcher import AgentDispatcher, AgentDispatchResult
from services.orchestrator.services.agent_runtime import AgentExecutionResult, AgentRuntime
from services.orchestrator.services.auditor_service import AuditorService
from services.orchestrator.services.specialist_service import SpecialistService
from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
from shared.concurrency import OptimisticLockError
from shared.config.state_transitions import is_terminal
from shared.models.registry import AuditLog, AuditResult, Workflow
from shared.schemas.task import StateTransitionRequest

logger = logging.getLogger(__name__)

MAX_WORKFLOW_RETRIES = 2
WORKFLOW_TIMEOUT_SECONDS = 1800


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ServiceResult:
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    error: str | None = None


@dataclass
class NodeResult:
    node_name: str
    status: str
    input_state: str
    output_state: str | None
    agent_result: AgentDispatchResult | AgentExecutionResult | ServiceResult | None
    error: str | None = None
    retry_count: int = 0


@dataclass
class WorkflowResult:
    task_id: UUID
    status: WorkflowStatus
    nodes: list[NodeResult] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    total_retries: int = 0
    error: str | None = None


class WorkflowEngine:
    def __init__(
        self,
        db: AsyncSession,
        agent_dispatcher: AgentDispatcher | None = None,
        agent_runtime: AgentRuntime | None = None,
        profile_builder: TaskProfileBuilder | None = None,
    ):
        self.db = db
        self.dispatcher = agent_dispatcher or AgentDispatcher(db)
        self.runtime = agent_runtime
        self.profile_builder = profile_builder
        if agent_runtime and profile_builder:
            self.specialist = SpecialistService(db, agent_runtime, agent_runtime.router, profile_builder)
            self.auditor = AuditorService(db, agent_runtime, profile_builder)
        else:
            self.specialist = None
            self.auditor = None
        self._history_store: dict[UUID, WorkflowResult] = {}
        self._saved_state: dict[UUID, dict] = {}

    async def run_workflow(self, task_id: UUID) -> WorkflowResult:
        task = await task_service.get_task(self.db, task_id)
        if not task:
            return WorkflowResult(task_id=task_id, status=WorkflowStatus.FAILED, error="Task not found")
        result = WorkflowResult(task_id=task_id, status=WorkflowStatus.RUNNING)
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        try:
            result = await asyncio.wait_for(
                self._run_workflow_loop(task, result, current_state),
                timeout=WORKFLOW_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.error(f"Workflow timed out for task {task_id} after {WORKFLOW_TIMEOUT_SECONDS}s")
            await self._transition_task(task, "ESCALATED", f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS}s")
            result.status = WorkflowStatus.FAILED
            result.error = f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS}s"
        except Exception as e:
            logger.error(f"Workflow failed for task {task_id}: {e}", exc_info=True)
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        return result

    async def _persist_workflow(self, task, result: WorkflowResult, current_state: str):
        from sqlalchemy import select
        from datetime import UTC, datetime
        query = select(Workflow).where(Workflow.task_id == task.id)
        res = await self.db.execute(query)
        wf = res.scalar_one_or_none()
        
        state_dict = {
            "total_cost_usd": result.total_cost_usd,
            "total_latency_ms": result.total_latency_ms,
            "total_retries": result.total_retries,
            "nodes": [
                {
                    "node": n.node_name,
                    "status": n.status,
                    "error": n.error,
                    "input_state": n.input_state,
                    "output_state": n.output_state,
                    "retry_count": n.retry_count,
                }
                for n in result.nodes
            ]
        }
        
        if not wf:
            wf = Workflow(
                project_id=task.project_id,
                task_id=task.id,
                name=f"workflow-{task.id.hex[:8]}",
                status=result.status.value,
                current_node=current_state,
                state=state_dict,
                started_at=datetime.now(UTC)
            )
            self.db.add(wf)
        else:
            wf.status = result.status.value
            wf.current_node = current_state
            wf.state = state_dict
            if is_terminal(current_state):
                wf.completed_at = datetime.now(UTC)
        try:
            await self.db.flush()
        except Exception as e:
            logger.warning(f"Failed to persist workflow state for {task.id}: {e}")

    async def _run_workflow_loop(self, task, result: WorkflowResult, current_state: str) -> WorkflowResult:
        retries_per_state: dict[str, int] = {}
        self._saved_state[task.id] = {"result": result, "current_state": current_state}
        await self._persist_workflow(task, result, current_state)
        
        while not is_terminal(current_state):
            node = await self._run_node(task, current_state)
            result.nodes.append(node)
            if node.agent_result:
                result.total_cost_usd += node.agent_result.cost_usd
                result.total_latency_ms += node.agent_result.latency_ms
            result.total_retries += node.retry_count
            self._history_store[task.id] = result
            self._saved_state[task.id] = {"result": result, "current_state": current_state}
            
            if node.node_name == "default":
                result.status = WorkflowStatus.FAILED
                result.error = node.error
                await self._persist_workflow(task, result, current_state)
                break
            
            if node.status == "failed":
                state_key = current_state
                retries_per_state[state_key] = retries_per_state.get(state_key, 0) + 1
                node.retry_count = retries_per_state[state_key]
                if retries_per_state[state_key] <= MAX_WORKFLOW_RETRIES:
                    await self._persist_workflow(task, result, current_state)
                    continue
                await self._transition_task(task, "ESCALATED", f"Max retries exceeded at {node.node_name}: {node.error}")
                result.status = WorkflowStatus.FAILED
                await self._persist_workflow(task, result, "ESCALATED")
                break
                
            if node.output_state:
                await self._transition_task(task, node.output_state, f"Node {node.node_name} completed")
                await self._log_audit(task, node)
                retries_per_state.clear()
                if is_terminal(node.output_state):
                    result.status = WorkflowStatus.COMPLETED
                    await self._persist_workflow(task, result, node.output_state)
                    break
            current_state = node.output_state or current_state
            await self._persist_workflow(task, result, current_state)
            
        return result

    async def _run_node(self, task, current_state: str) -> NodeResult:
        node_map = {
            "NEW": self._node_gatekeeper,
            "VALIDATING": self._node_validator,
            "ANALYZING": self._node_orchestrator,
            "PLANNING": self._node_orchestrator,
            "IMPLEMENTING": self._node_specialist,
            "VERIFYING": self._node_verification,
            "REVIEWING": self._node_auditor,
            "ESCALATED": self._node_mentor,
            "BLOCKED": self._node_blocked,
        }
        node_fn = node_map.get(current_state, self._node_default)
        return await node_fn(task)

    async def _node_gatekeeper(self, task) -> NodeResult:
        try:
            existing = await self.check_existing_task(task.id, task.description or task.title)
            memory_results = json.dumps({"existing_task": existing}) if existing else "{}"
            if self.runtime and self.profile_builder:
                profile = self.profile_builder.build(agent_name="gatekeeper")
                variables = {"user_request": task.description or task.title, "memory_results": memory_results}
                result = await self.runtime.execute_agent(agent_name="gatekeeper", task_id=task.id, task_profile=profile, variables=variables, project_id=task.project_id)
                if result.error:
                    return NodeResult(node_name="gatekeeper", status="failed", input_state="NEW", output_state=None, agent_result=result, error=result.error)
                parsed = result.parsed_output or {}
                agent_result = result
            else:
                agent_result = await self.dispatcher.dispatch_gatekeeper(task_id=task.id, project_id=task.project_id, user_request=task.description or task.title, memory_results=memory_results)
                if agent_result.error:
                    return NodeResult(node_name="gatekeeper", status="failed", input_state="NEW", output_state=None, agent_result=agent_result, error=agent_result.error)
                parsed = agent_result.parsed_output or {}
            risk_level = parsed.get("risk_level", "low")
            complexity = parsed.get("complexity", "trivial")
            if existing:
                return NodeResult(node_name="gatekeeper", status="completed", input_state="NEW", output_state="ANALYZING", agent_result=agent_result)
            if validation_service.should_skip_validation(risk_level, complexity):
                return NodeResult(node_name="gatekeeper", status="completed", input_state="NEW", output_state="ANALYZING", agent_result=agent_result)
            else:
                return NodeResult(node_name="gatekeeper", status="completed", input_state="NEW", output_state="VALIDATING", agent_result=agent_result)
        except Exception as e:
            logger.error(f"Gatekeeper node failed: {e}")
            return NodeResult(node_name="gatekeeper", status="failed", input_state="NEW", output_state=None, agent_result=None, error=str(e))

    async def _node_validator(self, task) -> NodeResult:
        try:
            user_request = task.description or task.title
            gatekeeper_output = {
                "task_type": "feature",
                "complexity": task.risk_level.value if hasattr(task.risk_level, "value") and task.risk_level else "medium",
                "risk_level": task.risk_level.value if hasattr(task.risk_level, "value") and task.risk_level else "medium",
                "effort": task.priority.value if hasattr(task.priority, "value") and task.priority else "medium",
            }
            verdict, confidence = validation_service.validate_classification(user_request=user_request, gatekeeper_classification=gatekeeper_output)
            if verdict == "APPROVED" and confidence >= 0.8:
                return NodeResult(node_name="validator", status="completed", input_state="VALIDATING", output_state="ANALYZING")
            elif verdict == "APPROVED" and confidence < 0.8:
                return NodeResult(node_name="validator", status="failed", input_state="VALIDATING", output_state=None, agent_result=None, error=f"Low confidence ({confidence}), requesting re-analysis")
            elif verdict == "NEEDS_REVIEW":
                return NodeResult(node_name="validator", status="completed", input_state="VALIDATING", output_state="ESCALATED", error="Validation needs mentor review")
            else:
                return NodeResult(node_name="validator", status="completed", input_state="VALIDATING", output_state="ESCALATED", error=f"Validation rejected: {verdict}")
        except Exception as e:
            logger.error(f"Validator node failed: {e}")
            return NodeResult(node_name="validator", status="failed", input_state="VALIDATING", output_state="ANALYZING", agent_result=None, error=f"Validation bypassed due to error: {e}")

    async def _node_orchestrator(self, task) -> NodeResult:
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        try:
            task_data = {"title": task.title, "description": task.description, "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority)}
            if self.runtime and self.profile_builder:
                profile = self.profile_builder.build(agent_name="orchestrator")
                variables = {"classified_task": json.dumps(task_data, default=str), "project_state": json.dumps({"modules": [], "tasks": []}, default=str)}
                result = await self.runtime.execute_agent(agent_name="orchestrator", task_id=task.id, task_profile=profile, variables=variables, project_id=task.project_id)
                if result.error:
                    return NodeResult(node_name="orchestrator", status="failed", input_state=current_state, output_state=None, agent_result=result, error=result.error)
                agent_result = result
            else:
                agent_result = await self.dispatcher.dispatch_orchestrator(task_id=task.id, project_id=task.project_id, classified_task=task_data, project_state={"modules": [], "tasks": []})
                if agent_result.error:
                    return NodeResult(node_name="orchestrator", status="failed", input_state=current_state, output_state=None, agent_result=agent_result, error=agent_result.error)
            next_state = "IMPLEMENTING" if current_state == "PLANNING" else "PLANNING"
            return NodeResult(node_name="orchestrator", status="completed", input_state=current_state, output_state=next_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="orchestrator", status="failed", input_state=current_state, output_state=None, agent_result=None, error=str(e))

    async def _node_specialist(self, task) -> NodeResult:
        try:
            task_spec = {"title": task.title, "description": task.description, "expected_output": task.expected_output}
            if self.specialist:
                result = await self.specialist.execute(task_id=task.id, task_spec=task_spec, context={})
                agent_result = ServiceResult(cost_usd=result.get("cost_usd", 0), latency_ms=result.get("latency_ms", 0), error=result.get("error"))
                if result["status"] == "failed":
                    return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=agent_result, error=result.get("error"))
                return NodeResult(node_name="specialist", status="completed", input_state="IMPLEMENTING", output_state="VERIFYING", agent_result=agent_result)
            elif self.runtime and self.profile_builder:
                profile = self.profile_builder.build(agent_name="specialist", requires_tools=True)
                variables = {"task_spec": json.dumps(task_spec, default=str, indent=2), "context": json.dumps({}, default=str, indent=2), "architectural_laws": ""}
                result = await self.runtime.execute_agent(agent_name="specialist", task_id=task.id, task_profile=profile, variables=variables, project_id=task.project_id)
                if result.error:
                    return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=result, error=result.error)
                return NodeResult(node_name="specialist", status="completed", input_state="IMPLEMENTING", output_state="VERIFYING", agent_result=result)
            else:
                agent_result = await self.dispatcher.dispatch_specialist(task_id=task.id, project_id=task.project_id, task_spec=task_spec, context={})
                if agent_result.error:
                    return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=agent_result, error=agent_result.error)
                return NodeResult(node_name="specialist", status="completed", input_state="IMPLEMENTING", output_state="VERIFYING", agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=None, error=str(e))

    async def _node_verification(self, task) -> NodeResult:
        try:
            from services.orchestrator.services.mode_selector import ModeSelector, handle_verification_fail
            from services.orchestrator.services.verification_service import VerificationPipeline
            risk_level = task.risk_level.value if hasattr(task.risk_level, "value") else str(task.risk_level) if task.risk_level else "LOW"
            mode = ModeSelector().select(risk_level)
            code_path = f"/tmp/workspace/{task.id.hex[:12]}"
            pipeline = VerificationPipeline()
            result = await pipeline.run_pipeline(task_id=task.id, code_path=code_path, mode=mode)
            retries = getattr(task, "verification_retries", 0)
            action = handle_verification_fail({"status": result.status, "score": result.score}, retries)
            agent_result = ServiceResult(cost_usd=0.0, latency_ms=result.duration_ms, error=None if action == "proceed" else f"Verification: {action}")
            if action == "proceed":
                return NodeResult(node_name="verification", status="completed", input_state="VERIFYING", output_state="REVIEWING", agent_result=agent_result)
            elif action == "retry":
                task.verification_retries = retries + 1
                return NodeResult(node_name="verification", status="failed", input_state="VERIFYING", output_state="VERIFYING", agent_result=agent_result, error=f"Verification failed (score={result.score}), retry {retries + 1}")
            else:
                return NodeResult(node_name="verification", status="failed", input_state="VERIFYING", output_state="ESCALATED", agent_result=agent_result, error=f"Verification failed after max retries (score={result.score})")
        except Exception as e:
            logger.error(f"Verification node failed: {e}")
            return NodeResult(node_name="verification", status="failed", input_state="VERIFYING", output_state="IMPLEMENTING", agent_result=None, error=str(e))

    async def _node_auditor(self, task) -> NodeResult:
        try:
            task_spec = {"title": task.title, "expected_output": task.expected_output}
            if self.auditor:
                result = await self.auditor.review(task_id=task.id, code=task.description or task.title, spec=task_spec, test_results={"status": "passed"})
                agent_result = ServiceResult(cost_usd=result.get("cost_usd", 0), latency_ms=result.get("latency_ms", 0), error=result.get("error"))
                verdict = result.get("verdict", "REVISE")
                output_state = "DONE" if verdict == "APPROVED" else ("IMPLEMENTING" if verdict == "REVISE" else "ESCALATED")
                return NodeResult(node_name="auditor", status="completed", input_state="REVIEWING", output_state=output_state, agent_result=agent_result)
            elif self.runtime and self.profile_builder:
                profile = self.profile_builder.build(agent_name="auditor")
                variables = {"code": (task.description or task.title)[:30000], "spec": json.dumps(task_spec, default=str), "test_results": json.dumps({"status": "passed"}, default=str), "laws": ""}
                result = await self.runtime.execute_agent(agent_name="auditor", task_id=task.id, task_profile=profile, variables=variables, project_id=task.project_id)
                if result.error:
                    return NodeResult(node_name="auditor", status="failed", input_state="REVIEWING", output_state=None, agent_result=result, error=result.error)
                parsed = result.parsed_output or {}
                verdict = parsed.get("verdict", "REVISE")
                output_state = "DONE" if verdict == "APPROVED" else ("IMPLEMENTING" if verdict == "REVISE" else "ESCALATED")
                return NodeResult(node_name="auditor", status="completed", input_state="REVIEWING", output_state=output_state, agent_result=result)
            else:
                agent_result = await self.dispatcher.dispatch_auditor(task_id=task.id, project_id=task.project_id, code=task.description or task.title, spec=task_spec, test_results={"status": "passed"})
                if agent_result.error:
                    return NodeResult(node_name="auditor", status="failed", input_state="REVIEWING", output_state=None, agent_result=agent_result, error=agent_result.error)
                verdict = agent_result.parsed_output.get("verdict", "REVISE") if agent_result.parsed_output else "REVISE"
                output_state = "DONE" if verdict == "APPROVED" else ("IMPLEMENTING" if verdict == "REVISE" else "ESCALATED")
                return NodeResult(node_name="auditor", status="completed", input_state="REVIEWING", output_state=output_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="auditor", status="failed", input_state="REVIEWING", output_state=None, agent_result=None, error=str(e))

    async def _node_mentor(self, task) -> NodeResult:
        try:
            if self.runtime and self.profile_builder:
                profile = self.profile_builder.build(agent_name="mentor")
                variables = {"task_history": json.dumps({"retries": task.retries, "status": str(task.status)}, default=str), "conflict_details": json.dumps({"reason": task.failure_reason or "escalated"}, default=str), "memory": json.dumps({}, default=str)}
                result = await self.runtime.execute_agent(agent_name="mentor", task_id=task.id, task_profile=profile, variables=variables, project_id=task.project_id)
                if result.error:
                    return NodeResult(node_name="mentor", status="failed", input_state="ESCALATED", output_state=None, agent_result=result, error=result.error)
                parsed = result.parsed_output or {}
                agent_result = result
            else:
                agent_result = await self.dispatcher.dispatch_mentor(task_id=task.id, project_id=task.project_id, task_history={"retries": task.retries, "status": str(task.status)}, conflict_details={"reason": task.failure_reason or "escalated"})
                if agent_result.error:
                    return NodeResult(node_name="mentor", status="failed", input_state="ESCALATED", output_state=None, agent_result=agent_result, error=agent_result.error)
                parsed = agent_result.parsed_output or {}
            verdict = parsed.get("verdict", "FAILED")
            output_state = "FAILED" if verdict in ("REJECT", "FAILED") else "PLANNING"
            return NodeResult(node_name="mentor", status="completed", input_state="ESCALATED", output_state=output_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="mentor", status="failed", input_state="ESCALATED", output_state=None, agent_result=None, error=str(e))

    async def _node_blocked(self, task) -> NodeResult:
        return NodeResult(node_name="blocked", status="failed", input_state="BLOCKED", output_state=None, agent_result=None, error="Task is blocked waiting for dependency resolution")

    async def _node_default(self, task) -> NodeResult:
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        return NodeResult(node_name="default", status="failed", input_state=current_state, output_state=None, agent_result=None, error=f"No handler for state {current_state}")

    async def _transition_task(self, task, new_status: str, reason: str) -> bool:
        try:
            _, error = await task_service.transition_task_state(self.db, task.id, StateTransitionRequest(target_status=new_status, reason=reason))
            if error:
                logger.warning(f"Failed to transition task {task.id} to {new_status}: {error}")
                return False
            return True
        except OptimisticLockError as e:
            logger.warning(f"Optimistic lock conflict on task {task.id}: {e}")
            return False

    async def _log_audit(self, task, node: NodeResult) -> None:
        try:
            log = AuditLog(
                task_id=task.id, action=f"workflow_node_{node.node_name}", actor="workflow_engine", actor_type="system",
                input={"state": node.input_state, "node": node.node_name},
                output={"state": node.output_state, "status": node.status},
                result=AuditResult.SUCCESS if node.status == "completed" else AuditResult.FAILURE,
                message=f"Node {node.node_name}: {node.input_state} -> {node.output_state}",
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.warning(f"Failed to create audit log for node {node.node_name}: {e}")

    async def cancel_workflow(self, task_id: UUID) -> bool:
        task = await task_service.get_task(self.db, task_id)
        if not task:
            return False
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        if is_terminal(current_state):
            return False
        return await self._transition_task(task, "CANCELLED", "Cancelled by user")

    async def resume_workflow(self, task_id: UUID) -> WorkflowResult | None:
        task = await task_service.get_task(self.db, task_id)
        if not task:
            return None
        saved = self._saved_state.get(task_id)
        if not saved:
            return None
        result = saved.get("result", WorkflowResult(task_id=task_id, status=WorkflowStatus.RUNNING))
        current_state = saved.get("current_state", task.status.value if hasattr(task.status, "value") else str(task.status))
        if is_terminal(current_state):
            return result
        result = await self._run_workflow_loop(task, result, current_state)
        self._history_store[task_id] = result
        return result

    async def get_workflow_status(self, task_id: UUID) -> dict | None:
        from sqlalchemy import select
        res = await self.db.execute(select(Workflow).where(Workflow.task_id == task_id))
        wf = res.scalar_one_or_none()
        if not wf:
            return None
            
        nodes = wf.state.get("nodes", [])
        last_node = nodes[-1] if nodes else None
        return {
            "task_id": str(task_id),
            "status": wf.status,
            "current_node": last_node.get("node") if last_node else None,
            "nodes_completed": len(nodes),
            "total_retries": wf.state.get("total_retries", 0),
            "total_cost_usd": round(wf.state.get("total_cost_usd", 0.0), 4),
            "total_latency_ms": round(wf.state.get("total_latency_ms", 0.0), 2),
            "error": wf.error,
        }

    async def get_workflow_history(self, task_id: UUID) -> list[dict] | None:
        from sqlalchemy import select
        res = await self.db.execute(select(Workflow).where(Workflow.task_id == task_id))
        wf = res.scalar_one_or_none()
        if not wf:
            return None
        return wf.state.get("nodes", [])

    async def check_existing_task(self, task_id: UUID, task_description: str) -> dict | None:
        from sqlalchemy import select
        res = await self.db.execute(select(Workflow).where(Workflow.status == "COMPLETED").limit(10))
        workflows = res.scalars().all()
        for wf in workflows:
            if wf.task_id == task_id:
                continue
            nodes = wf.state.get("nodes", [])
            for node in nodes:
                if node.get("node") == "gatekeeper" and node.get("output_state") == "ANALYZING":
                    return {"existing_task_id": str(wf.task_id), "cached": True}
        return None
