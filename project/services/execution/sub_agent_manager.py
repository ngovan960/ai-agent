import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.execution.sandboxed_opencode_adapter import SandboxedOpenCodeAdapter

logger = logging.getLogger(__name__)


@dataclass
class SubAgent:
    agent_id: str
    task_id: UUID
    status: str
    context: dict
    created_at: str
    result: dict | None = None
    error: str | None = None


class FileLock:
    """File-level locking for concurrent sub-agent execution."""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}

    async def acquire(self, file_path: str) -> bool:
        if file_path not in self._locks:
            self._locks[file_path] = asyncio.Lock()
        lock = self._locks[file_path]
        try:
            await asyncio.wait_for(lock.acquire(), timeout=30.0)
            return True
        except TimeoutError:
            logger.error(f"Could not acquire lock for {file_path} (timeout)")
            return False

    def release(self, file_path: str) -> None:
        lock = self._locks.get(file_path)
        if lock and lock.locked():
            lock.release()

    def is_locked(self, file_path: str) -> bool:
        lock = self._locks.get(file_path)
        return lock is not None and lock.locked()


class SubAgentManager:
    def __init__(self, target_project_path: str | None = None):
        self._agents: dict[str, SubAgent] = {}
        self._adapter = SandboxedOpenCodeAdapter(
            target_project_path=target_project_path or "/workspace/project"
        )
        self._file_lock = FileLock()

    async def create_sub_agent(self, task_id: UUID, context: dict) -> str:
        agent_id = f"sub-{task_id.hex[:8]}-{uuid4().hex[:8]}"
        agent = SubAgent(
            agent_id=agent_id, task_id=task_id, status="created",
            context=context, created_at=datetime.now(UTC).isoformat(),
        )
        self._agents[agent_id] = agent
        logger.info(f"Sub-agent created: {agent_id}")
        return agent_id

    async def execute_sub_agent(self, agent_id: str, task_spec: str, timeout: int = 300) -> dict:
        agent = self._agents.get(agent_id)
        if not agent:
            return {"status": "failed", "error": f"Sub-agent {agent_id} not found"}
        agent.status = "running"

        files_to_modify = []

        try:
            if isinstance(task_spec, dict):
                files_to_modify = task_spec.get("files_to_modify", [])
            elif isinstance(task_spec, str):
                import json
                try:
                    parsed = json.loads(task_spec)
                    files_to_modify = parsed.get("files_to_modify", [])
                except json.JSONDecodeError:
                    pass

            locked_files = []
            for fpath in files_to_modify:
                if await self._file_lock.acquire(fpath):
                    locked_files.append(fpath)

            try:
                result = await asyncio.wait_for(
                    self._adapter.execute(agent.task_id, task_spec, agent.context),
                    timeout=timeout,
                )
                agent.status = "completed"
                agent.result = {"output": result}
                return {"status": "completed", "result": result}
            finally:
                for fpath in locked_files:
                    self._file_lock.release(fpath)

        except TimeoutError:
            agent.status = "failed"
            agent.error = f"Timeout after {timeout}s"
            return {"status": "failed", "error": agent.error}
        except Exception as e:
            agent.status = "failed"
            agent.error = str(e)
            return {"status": "failed", "error": str(e)}

    async def get_sub_agent(self, agent_id: str) -> SubAgent | None:
        return self._agents.get(agent_id)

    async def collect_results(self, agent_id: str) -> dict | None:
        agent = self._agents.get(agent_id)
        if not agent or agent.status != "completed":
            return None
        return agent.result

    async def destroy_sub_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
