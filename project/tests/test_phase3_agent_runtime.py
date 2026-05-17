from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.model_router import Model, SpeedCategory, TaskType


def _make_mock_models():
    return [
        Model(
            name="deepseek_v4_flash",
            provider="deepseek",
            context_window=131072,
            max_output_tokens=8192,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0003,
            timeout_seconds=15,
            speed_category=SpeedCategory.VERY_FAST,
            capabilities={"classification": 90, "code_generation": 50, "review": 30, "planning": 40, "decision": 20, "monitoring": 80},
            strengths=["fast classification", "low cost"],
            weaknesses=["limited reasoning"],
            best_for=["classification", "monitoring"],
            avoid_for=["complex planning"],
        ),
        Model(
            name="deepseek_v4_pro",
            provider="deepseek",
            context_window=131072,
            max_output_tokens=8192,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            timeout_seconds=60,
            speed_category=SpeedCategory.FAST,
            capabilities={"classification": 70, "code_generation": 90, "review": 60, "planning": 60, "decision": 40, "monitoring": 50},
            strengths=["code generation", "reasoning"],
            weaknesses=["slower than flash"],
            best_for=["code_generation"],
            avoid_for=["real-time"],
        ),
    ]


@pytest.mark.asyncio
class TestTaskProfileBuilder:
    async def test_build_gatekeeper_profile(self, test_db: AsyncSession):
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter, SpeedRequirement

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)
        profile = builder.build(agent_name="gatekeeper")

        assert profile.task_type == TaskType.CLASSIFICATION
        assert profile.speed_requirement == SpeedRequirement.FAST

    async def test_build_specialist_profile(self, test_db: AsyncSession):
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)
        profile = builder.build(agent_name="specialist", requires_tools=True)

        assert profile.task_type == TaskType.CODE_GENERATION
        assert profile.requires_tools is True

    async def test_build_with_complexity_risk(self, test_db: AsyncSession):
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)

        low_profile = builder.build(agent_name="gatekeeper", complexity="trivial", risk_level="low")
        high_profile = builder.build(agent_name="gatekeeper", complexity="critical", risk_level="critical")

        assert low_profile.complexity < high_profile.complexity

    async def test_agent_to_state_mapping(self, test_db: AsyncSession):
        from services.orchestrator.services.task_profile_builder import AGENT_TO_STATE

        assert AGENT_TO_STATE["gatekeeper"] == "NEW"
        assert AGENT_TO_STATE["validator"] == "VALIDATING"
        assert AGENT_TO_STATE["orchestrator"] == "ANALYZING"
        assert AGENT_TO_STATE["specialist"] == "IMPLEMENTING"
        assert AGENT_TO_STATE["auditor"] == "REVIEWING"
        assert AGENT_TO_STATE["mentor"] == "ESCALATED"

    async def test_select_model_integration(self, test_db: AsyncSession):
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)

        profile = builder.build(agent_name="gatekeeper")
        selection = router.select(profile)

        assert selection.primary is not None
        assert len(selection.fallbacks) >= 0
        assert selection.llm_path.value == "opencode"


@pytest.mark.asyncio
class TestAgentRuntime:
    async def test_execute_agent_handles_no_model(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from shared.config.model_router import ModelRouter, TaskProfile

        router = ModelRouter(models=[])
        runtime = AgentRuntime(test_db, router)

        profile = TaskProfile(task_type=TaskType.CLASSIFICATION)
        result = await runtime.execute_agent(
            agent_name="gatekeeper",
            task_id=uuid4(),
            task_profile=profile,
            variables={"user_request": "test"},
        )

        assert result.error is not None

    async def test_escalate_task(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from services.orchestrator.services.tasks import create_task
        from shared.config.model_router import ModelRouter
        from shared.schemas.task import TaskCreate

        task_create = TaskCreate(
            project_id=uuid4(),
            title="Test escalation",
            description="Test",
        )
        task = await create_task(db=test_db, data=task_create)
        await test_db.commit()

        router = ModelRouter(models=_make_mock_models())
        runtime = AgentRuntime(test_db, router)

        record = await runtime.escalate_task(
            task_id=task.id,
            reason="Test escalation",
            severity="HIGH",
        )

        assert record.task_id == task.id
        assert record.severity == "HIGH"

    async def test_retry_agent_creates_retry_variables(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from shared.config.model_router import ModelRouter, TaskProfile

        router = ModelRouter(models=_make_mock_models())
        runtime = AgentRuntime(test_db, router)

        profile = TaskProfile(task_type=TaskType.CLASSIFICATION)
        result = await runtime.retry_agent(
            agent_name="gatekeeper",
            task_id=uuid4(),
            task_profile=profile,
            variables={"user_request": "test"},
            previous_output="{}",
            error="Previous attempt failed with parse error",
        )

        assert result.error is not None or result.model_used != ""

    async def test_parse_json_output(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        runtime = AgentRuntime(test_db, router)

        parsed = runtime._parse_output("gatekeeper", '{"verdict": "APPROVED"}')
        assert parsed is not None
        assert parsed.get("verdict") == "APPROVED"

    async def test_parse_specialist_text_output(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        runtime = AgentRuntime(test_db, router)

        parsed = runtime._parse_output("specialist", "def hello():\n    pass")
        assert parsed is not None
        assert "raw_code" in parsed


@pytest.mark.asyncio
class TestPromptTemplates:
    async def test_load_validator_template(self, test_db: AsyncSession):
        from services.orchestrator.services.prompt_templates import PromptTemplateLoader

        loader = PromptTemplateLoader()
        template = loader.load_template("validator")
        assert template is not None
        assert len(template) > 200
        assert "Validator Agent" in template

    async def test_load_all_templates(self, test_db: AsyncSession):
        from services.orchestrator.services.prompt_templates import PromptTemplateLoader

        loader = PromptTemplateLoader()
        agents = ["gatekeeper", "validator", "orchestrator", "specialist", "auditor", "mentor", "devops", "monitoring"]
        for agent in agents:
            template = loader.load_template(agent)
            assert template is not None, f"Template for {agent} should exist"

    async def test_render_with_variables(self, test_db: AsyncSession):
        from services.orchestrator.services.prompt_templates import PromptTemplateLoader

        loader = PromptTemplateLoader()
        rendered = loader.render(
            "gatekeeper",
            variables={
                "user_request": "Build login feature",
                "memory_results": "{}",
            },
        )
        assert "Build login feature" in rendered

    async def test_self_awareness_injection(self, test_db: AsyncSession):
        from services.orchestrator.services.prompt_templates import PromptTemplateLoader

        loader = PromptTemplateLoader()
        system_prompt = "You are the Gatekeeper Agent."

        injected = loader.inject_self_awareness("deepseek_v4_flash", system_prompt)
        assert "SELF-AWARENESS" in injected

    async def test_build_messages_with_model_name(self, test_db: AsyncSession):
        from services.orchestrator.services.prompt_templates import PromptTemplateLoader

        loader = PromptTemplateLoader()
        messages = loader.build_messages(
            agent_name="gatekeeper",
            variables={"user_request": "test", "memory_results": "{}"},
            model_name="deepseek_v4_flash",
        )
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"


@pytest.mark.asyncio
class TestOpenCodeAdapter:
    async def test_read_write_file(self, test_db: AsyncSession):
        import os
        import tempfile

        from services.execution.opencode_adapter import OpenCodeAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = OpenCodeAdapter(project_root=tmpdir)
            path = "src/test.txt"
            written = await adapter.write_file(path, "hello world")
            assert written is True

            content = await adapter.read_file(path)
            assert content == "hello world"

    async def test_edit_file(self, test_db: AsyncSession):
        import os
        import tempfile

        from services.execution.opencode_adapter import OpenCodeAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = OpenCodeAdapter(project_root=tmpdir)
            path = "src/edit_test.txt"
            await adapter.write_file(path, "old content")
            await adapter.edit_file(path, "old content", "new content")

            content = await adapter.read_file(path)
            assert content == "new content"

    async def test_edit_file_fails_if_not_found(self, test_db: AsyncSession):
        import os
        import tempfile

        from services.execution.opencode_adapter import OpenCodeAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = OpenCodeAdapter(project_root=tmpdir)
            path = "src/missing.txt"
            result = await adapter.edit_file(path, "old", "new")
            assert result is False

    async def test_execute_returns_result(self, test_db: AsyncSession):
        from services.execution.opencode_adapter import OpenCodeAdapter

        adapter = OpenCodeAdapter()
        result = await adapter.execute(
            task_spec={"title": "Test", "files_to_create": [], "files_to_modify": [], "verification": ""},
            context={},
        )
        assert result.status == "completed"
        assert result.agent_id is not None


@pytest.mark.asyncio
class TestSpecialistService:
    async def test_create_service(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from services.orchestrator.services.specialist_service import SpecialistService
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)
        runtime = AgentRuntime(test_db, router)
        service = SpecialistService(test_db, runtime, router, builder)

        assert service is not None


@pytest.mark.asyncio
class TestAuditorService:
    async def test_create_service(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from services.orchestrator.services.auditor_service import AuditorService
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)
        runtime = AgentRuntime(test_db, router)
        service = AuditorService(test_db, runtime, builder)

        assert service is not None

    async def test_check_laws(self, test_db: AsyncSession):
        from services.orchestrator.services.agent_runtime import AgentRuntime
        from services.orchestrator.services.auditor_service import AuditorService
        from services.orchestrator.services.task_profile_builder import TaskProfileBuilder
        from shared.config.model_router import ModelRouter

        router = ModelRouter(models=_make_mock_models())
        builder = TaskProfileBuilder(router)
        runtime = AgentRuntime(test_db, router)
        service = AuditorService(test_db, runtime, builder)

        violations = await service.check_laws(uuid4(), 'password = "secret123"')
        assert len(violations) >= 1
        assert violations[0]["law"] == "LAW-005"
