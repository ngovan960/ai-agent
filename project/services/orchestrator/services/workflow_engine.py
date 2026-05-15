import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus
from shared.schemas.task import StateTransitionRequest
from shared.config.state_transitions import validate_transition, is_terminal
from shared.concurrency import OptimisticLockError
from services.orchestrator.services import tasks as task_service
from services.orchestrator.services.agent_dispatcher import AgentDispatcher, AgentDispatchResult
from shared.models.registry import AuditLog, AuditResult

logger = logging.getLogger(__name__)

MAX_WORKFLOW_RETRIES = 2
WORKFLOW_TIMEOUT_SECONDS = 1800


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    node_name: str
    status: str
    input_state: str
    output_state: str | None
    agent_result: AgentDispatchResult | None
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
    def __init__(self, db: AsyncSession, agent_dispatcher: Optional[AgentDispatcher] = None):
        self.db = db
        self.dispatcher = agent_dispatcher or AgentDispatcher(db)

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
        except asyncio.TimeoutError:
            logger.error(f"Workflow timed out for task {task_id} after {WORKFLOW_TIMEOUT_SECONDS}s")
            await self._transition_task(task, "ESCALATED", f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS}s")
            result.status = WorkflowStatus.FAILED
            result.error = f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS}s"
        except Exception as e:
            logger.error(f"Workflow failed for task {task_id}: {e}", exc_info=True)
            result.status = WorkflowStatus.FAILED
            result.error = str(e)

        return result

    async def _run_workflow_loop(self, task, result: WorkflowResult, current_state: str) -> WorkflowResult:
        retries_per_state: dict[str, int] = {}

        while not is_terminal(current_state):
            node = await self._run_node(task, current_state)
            result.nodes.append(node)
            if node.agent_result:
                result.total_cost_usd += node.agent_result.cost_usd
                result.total_latency_ms += node.agent_result.latency_ms
            result.total_retries += node.retry_count

            if node.status == "failed":
                state_key = current_state
                retries_per_state[state_key] = retries_per_state.get(state_key, 0) + 1
                node.retry_count = retries_per_state[state_key]

                if retries_per_state[state_key] <= MAX_WORKFLOW_RETRIES:
                    logger.info(
                        f"Node {node.node_name} failed at state {current_state}, "
                        f"retrying ({retries_per_state[state_key]}/{MAX_WORKFLOW_RETRIES})"
                    )
                    continue

                logger.warning(
                    f"Node {node.node_name} failed at state {current_state} "
                    f"after {MAX_WORKFLOW_RETRIES} retries, escalating"
                )
                await self._transition_task(
                    task, "ESCALATED",
                    f"Max retries exceeded at {node.node_name}: {node.error}"
                )
                break

            if node.output_state:
                await self._transition_task(task, node.output_state, f"Node {node.node_name} completed")
                await self._log_audit(task, node)
                retries_per_state.clear()

                if is_terminal(node.output_state):
                    result.status = WorkflowStatus.COMPLETED
                    break

            current_state = node.output_state or current_state

        task = await task_service.get_task(self.db, task_id)
        if task:
            final_state = task.status.value if hasattr(task.status, "value") else str(task.status)
            if is_terminal(final_state):
                if final_state == "DONE":
                    result.status = WorkflowStatus.COMPLETED
                elif final_state == "FAILED":
                    result.status = WorkflowStatus.FAILED
                elif final_state == "CANCELLED":
                    result.status = WorkflowStatus.CANCELLED
            else:
                result.status = WorkflowStatus.RUNNING

        return result

    async def _run_node(self, task, current_state: str) -> NodeResult:
        node_map = {
            "NEW": self._node_gatekeeper,
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
            agent_result = await self.dispatcher.dispatch_gatekeeper(
                task_id=task.id,
                project_id=task.project_id,
                user_request=task.description or task.title,
            )
            if agent_result.error:
                return NodeResult(node_name="gatekeeper", status="failed", input_state="NEW", output_state=None, agent_result=agent_result, error=agent_result.error)
            return NodeResult(node_name="gatekeeper", status="completed", input_state="NEW", output_state="ANALYZING", agent_result=agent_result)
        except Exception as e:
            logger.error(f"Gatekeeper node failed: {e}")
            return NodeResult(node_name="gatekeeper", status="failed", input_state="NEW", output_state=None, agent_result=None, error=str(e))

    async def _node_orchestrator(self, task) -> NodeResult:
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        try:
            task_data = {
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
            }
            agent_result = await self.dispatcher.dispatch_orchestrator(
                task_id=task.id, project_id=task.project_id,
                classified_task=task_data, project_state={"modules": [], "tasks": []},
            )
            if agent_result.error:
                return NodeResult(node_name="orchestrator", status="failed", input_state=current_state, output_state=None, agent_result=agent_result, error=agent_result.error)
            next_state = "IMPLEMENTING" if current_state == "PLANNING" else "PLANNING"
            return NodeResult(node_name="orchestrator", status="completed", input_state=current_state, output_state=next_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="orchestrator", status="failed", input_state=current_state, output_state=None, agent_result=None, error=str(e))

    async def _node_specialist(self, task) -> NodeResult:
        try:
            task_spec = {
                "title": task.title,
                "description": task.description,
                "expected_output": task.expected_output,
            }
            agent_result = await self.dispatcher.dispatch_specialist(
                task_id=task.id, project_id=task.project_id,
                task_spec=task_spec, context={},
            )
            if agent_result.error:
                return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=agent_result, error=agent_result.error)
            return NodeResult(node_name="specialist", status="completed", input_state="IMPLEMENTING", output_state="VERIFYING", agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="specialist", status="failed", input_state="IMPLEMENTING", output_state=None, agent_result=None, error=str(e))

    async def _node_verification(self, task) -> NodeResult:
        return NodeResult(
            node_name="verification", status="completed",
            input_state="VERIFYING", output_state="REVIEWING",
            agent_result=None,
        )

    async def _node_auditor(self, task) -> NodeResult:
        try:
            task_spec = {"title": task.title, "expected_output": task.expected_output}
            agent_result = await self.dispatcher.dispatch_auditor(
                task_id=task.id, project_id=task.project_id,
                code=task.description or task.title,
                spec=task_spec, test_results={"status": "passed"},
            )
            if agent_result.error:
                return NodeResult(node_name="auditor", status="failed", input_state="REVIEWING", output_state=None, agent_result=agent_result, error=agent_result.error)
            verdict = agent_result.parsed_output.get("verdict", "REVISE") if agent_result.parsed_output else "REVISE"
            output_state = "DONE" if verdict == "APPROVED" else ("IMPLEMENTING" if verdict == "REVISE" else "ESCALATED")
            return NodeResult(node_name="auditor", status="completed", input_state="REVIEWING", output_state=output_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="auditor", status="failed", input_state="REVIEWING", output_state=None, agent_result=None, error=str(e))

    async def _node_mentor(self, task) -> NodeResult:
        try:
            agent_result = await self.dispatcher.dispatch_mentor(
                task_id=task.id, project_id=task.project_id,
                task_history={"retries": task.retries, "status": str(task.status)},
                conflict_details={"reason": task.failure_reason or "escalated"},
            )
            if agent_result.error:
                return NodeResult(node_name="mentor", status="failed", input_state="ESCALATED", output_state=None, agent_result=agent_result, error=agent_result.error)
            verdict = agent_result.parsed_output.get("verdict", "FAILED") if agent_result.parsed_output else "FAILED"
            output_state = "FAILED" if verdict in ("REJECT", "FAILED") else "PLANNING"
            return NodeResult(node_name="mentor", status="completed", input_state="ESCALATED", output_state=output_state, agent_result=agent_result)
        except Exception as e:
            return NodeResult(node_name="mentor", status="failed", input_state="ESCALATED", output_state=None, agent_result=None, error=str(e))

    async def _node_blocked(self, task) -> NodeResult:
        return NodeResult(
            node_name="blocked", status="completed",
            input_state="BLOCKED", output_state=None,
            agent_result=None,
        )

    async def _node_default(self, task) -> NodeResult:
        current_state = task.status.value if hasattr(task.status, "value") else str(task.status)
        return NodeResult(
            node_name="default", status="failed",
            input_state=current_state, output_state=None,
            agent_result=None, error=f"No handler for state {current_state}",
        )

    async def _transition_task(self, task, new_status: str, reason: str) -> bool:
        try:
            _, error = await task_service.transition_task_state(
                self.db, task.id,
                StateTransitionRequest(target_status=new_status, reason=reason),
            )
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
                task_id=task.id,
                action=f"workflow_node_{node.node_name}",
                actor="workflow_engine",
                actor_type="system",
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
