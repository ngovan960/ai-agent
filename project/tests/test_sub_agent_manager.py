from uuid import uuid4

import pytest

from services.execution.sub_agent_manager import SubAgentManager


class TestSubAgentManager:
    @pytest.mark.asyncio
    async def test_create_manager(self):
        mgr = SubAgentManager()
        assert mgr is not None

    @pytest.mark.asyncio
    async def test_create_sub_agent(self):
        mgr = SubAgentManager()
        agent_id = await mgr.create_sub_agent(uuid4(), {"path": "/tmp"})
        assert agent_id is not None
        assert agent_id.startswith("sub-")

    @pytest.mark.asyncio
    async def test_get_sub_agent(self):
        mgr = SubAgentManager()
        task_id = uuid4()
        agent_id = await mgr.create_sub_agent(task_id, {})
        agent = await mgr.get_sub_agent(agent_id)
        assert agent is not None
        assert agent.task_id == task_id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        mgr = SubAgentManager()
        agent = await mgr.get_sub_agent("nonexistent")
        assert agent is None

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self):
        mgr = SubAgentManager()
        result = await mgr.execute_sub_agent("nonexistent", "task")
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_collect_results(self):
        mgr = SubAgentManager()
        result = await mgr.collect_results("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_destroy(self):
        mgr = SubAgentManager()
        agent_id = await mgr.create_sub_agent(uuid4(), {})
        assert await mgr.destroy_sub_agent(agent_id) is True
        assert await mgr.destroy_sub_agent(agent_id) is False
