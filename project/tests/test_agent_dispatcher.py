import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.orchestrator.services.agent_dispatcher import (
    AgentDispatcher,
    AgentDispatchResult,
    STATE_AGENT_MAP,
    AGENT_CONFIG,
)
from services.orchestrator.services.prompt_templates import PromptTemplateLoader


class TestPromptTemplateLoader:
    def test_load_template_fallback(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        template = loader.load_template("gatekeeper")
        assert "User request:" in template
        assert "{user_request}" in template

    def test_render_substitutes_variables(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        rendered = loader.render("gatekeeper", {
            "user_request": "Build a login page",
            "memory_results": "no past results",
        })
        assert "Build a login page" in rendered
        assert "no past results" in rendered

    def test_build_messages_includes_system_prompt(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        messages = loader.build_messages(
            "gatekeeper",
            {"user_request": "test", "memory_results": "none"},
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Gatekeeper" in messages[0]["content"]

    def test_build_messages_with_context(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        messages = loader.build_messages(
            "auditor",
            {"code": "def foo(): pass", "spec": "{}", "test_results": "{}", "laws": ""},
            context_sections=[
                {"name": "Task Spec", "content": "Implement auth"},
                {"name": "Laws", "content": "LAW-001: no business logic in controller"},
            ],
        )
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "system"
        assert "Implement auth" in messages[1]["content"]
        assert messages[2]["role"] == "system"
        assert "LAW-001" in messages[2]["content"]

    def test_custom_system_prompt(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        messages = loader.build_messages(
            "gatekeeper",
            {"user_request": "test", "memory_results": "none"},
            system_prompt="Custom system prompt",
        )
        assert messages[0]["content"] == "Custom system prompt"

    def test_all_agents_have_default_templates(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        for agent in ["gatekeeper", "orchestrator", "specialist", "auditor", "mentor", "devops", "monitoring"]:
            template = loader.load_template(agent)
            assert template, f"Missing template for {agent}"

    def test_render_ignores_missing_variables(self):
        loader = PromptTemplateLoader(prompts_dir=None)
        rendered = loader.render("gatekeeper", {"user_request": "test"})
        assert "test" in rendered
        assert "{memory_results}" in rendered


class TestAgentDispatcherConfig:
    def test_state_agent_map_all_states(self):
        expected_states = {"NEW", "ANALYZING", "PLANNING", "IMPLEMENTING", "VERIFYING", "REVIEWING", "ESCALATED", "BLOCKED", "FAILED"}
        for state in expected_states:
            assert state in STATE_AGENT_MAP, f"Missing agent for state {state}"

    def test_get_agent_for_state(self):
        mock_db = MagicMock()
        dispatcher = AgentDispatcher(mock_db)
        assert dispatcher.get_agent_for_state("NEW") == "gatekeeper"
        assert dispatcher.get_agent_for_state("IMPLEMENTING") == "specialist"
        assert dispatcher.get_agent_for_state("REVIEWING") == "auditor"
        assert dispatcher.get_agent_for_state("ESCALATED") == "mentor"
        assert dispatcher.get_agent_for_state("ANALYZING") == "orchestrator"
        assert dispatcher.get_agent_for_state("BLOCKED") == "orchestrator"

    def test_get_agent_config(self):
        mock_db = MagicMock()
        dispatcher = AgentDispatcher(mock_db)
        config = dispatcher.get_agent_config("gatekeeper")
        assert config["primary_model"] == "deepseek_v4_flash"
        assert config["timeout"] == 15

        config = dispatcher.get_agent_config("mentor")
        assert config["primary_model"] == "qwen_3_6_plus"
        assert config["timeout"] == 90

    def test_all_agents_have_config(self):
        for agent in STATE_AGENT_MAP.values():
            if agent != "system":
                assert agent in AGENT_CONFIG, f"Missing config for {agent}"

    def test_parse_output_json(self):
        content = '{"verdict": "APPROVED", "confidence": 0.95}'
        result = AgentDispatcher._parse_output("gatekeeper", content)
        assert result == {"verdict": "APPROVED", "confidence": 0.95}

    def test_parse_output_non_json(self):
        result = AgentDispatcher._parse_output("specialist", "FILE: test.py\n```python\nprint('hello')\n```")
        assert result is None

    def test_parse_output_empty(self):
        assert AgentDispatcher._parse_output("gatekeeper", "") is None
        assert AgentDispatcher._parse_output("gatekeeper", None) is None

    def test_parse_output_invalid_json(self):
        result = AgentDispatcher._parse_output("gatekeeper", "not json at all")
        assert result is None


class TestAgentDispatcherDispatch:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_gateway(self):
        gw = MagicMock()
        gw.call = AsyncMock()
        return gw

    @pytest.fixture
    def dispatcher(self, mock_db, mock_gateway):
        return AgentDispatcher(db=mock_db, llm_gateway=mock_gateway)

    async def test_dispatch_gatekeeper(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content='{"intent": "add_feature", "complexity_score": 5}',
            model="deepseek_v4_flash",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.0001,
            latency_ms=300,
            status="completed",
        )
        result = await dispatcher.dispatch_gatekeeper(
            task_id=uuid4(),
            project_id=uuid4(),
            user_request="Build a login page",
        )
        assert result.agent_name == "gatekeeper"
        assert result.parsed_output is not None
        assert mock_gateway.call.called

    async def test_dispatch_orchestrator(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content='{"task_breakdown": [], "workflow_plan": {}}',
            model="qwen_3_6_plus",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.001,
            latency_ms=500,
            status="completed",
        )
        result = await dispatcher.dispatch_orchestrator(
            task_id=uuid4(),
            project_id=uuid4(),
            classified_task={"intent": "add_feature"},
            project_state={"modules": []},
        )
        assert result.agent_name == "orchestrator"
        assert mock_gateway.call.called

    async def test_dispatch_specialist(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content="FILE: app.py\n```python\ndef hello(): pass\n```",
            model="deepseek_v4_pro",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.002,
            latency_ms=800,
            status="completed",
        )
        result = await dispatcher.dispatch_specialist(
            task_id=uuid4(),
            project_id=uuid4(),
            task_spec={"title": "auth module"},
            context={"modules": []},
        )
        assert result.agent_name == "specialist"
        assert result.parsed_output is None

    async def test_dispatch_auditor(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content='{"verdict": "APPROVED", "scores": {"overall": 0.85}}',
            model="qwen_3_5_plus",
            input_tokens=1500,
            output_tokens=300,
            cost_usd=0.001,
            latency_ms=400,
            status="completed",
        )
        result = await dispatcher.dispatch_auditor(
            task_id=uuid4(),
            project_id=uuid4(),
            code="def hello(): pass",
            spec={"title": "test"},
            test_results={"passed": True},
        )
        assert result.agent_name == "auditor"
        assert result.parsed_output == {"verdict": "APPROVED", "scores": {"overall": 0.85}}

    async def test_dispatch_mentor(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content='{"verdict": "REJECT", "reason": "too complex"}',
            model="qwen_3_6_plus",
            input_tokens=2000,
            output_tokens=400,
            cost_usd=0.002,
            latency_ms=600,
            status="completed",
        )
        result = await dispatcher.dispatch_mentor(
            task_id=uuid4(),
            project_id=uuid4(),
            task_history={"retries": 3},
            conflict_details={"errors": ["timeout"]},
        )
        assert result.agent_name == "mentor"
        assert result.parsed_output["verdict"] == "REJECT"

    async def test_dispatch_force_agent(self, dispatcher, mock_gateway):
        mock_gateway.call.return_value = MagicMock(
            content="ok",
            model="deepseek_v4_pro",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0001,
            latency_ms=100,
            status="completed",
        )
        result = await dispatcher.dispatch(
            task_id=uuid4(),
            project_id=uuid4(),
            current_state="ANALYZING",
            variables={"input": "test"},
            force_agent="specialist",
        )
        assert result.agent_name == "specialist"
