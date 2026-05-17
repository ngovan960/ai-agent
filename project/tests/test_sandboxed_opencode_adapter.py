from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.execution.sandboxed_opencode_adapter import (
    SandboxedOpenCodeAdapter,
)


class TestProtectedPathDetection:
    def test_protected_laws_yaml(self):
        adapter = SandboxedOpenCodeAdapter()
        assert adapter._is_protected_path("shared/config/laws.yaml") is True
        assert adapter._is_protected_path("/shared/config/laws.yaml") is True

    def test_protected_env(self):
        adapter = SandboxedOpenCodeAdapter()
        assert adapter._is_protected_path(".env") is True
        assert adapter._is_protected_path(".env.local") is True

    def test_protected_services(self):
        adapter = SandboxedOpenCodeAdapter()
        assert adapter._is_protected_path("services/orchestrator/main.py") is True

    def test_protected_agents(self):
        adapter = SandboxedOpenCodeAdapter()
        assert adapter._is_protected_path("agents/prompts/gatekeeper.txt") is True

    def test_safe_project_file(self):
        adapter = SandboxedOpenCodeAdapter()
        assert adapter._is_protected_path("src/main.py") is False
        assert adapter._is_protected_path("services/my_service.py") is False
        assert adapter._is_protected_path("tests/test_main.py") is False


class TestSandboxSession:
    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_create_session_no_project_path(self, mock_run):
        adapter = SandboxedOpenCodeAdapter(target_project_path=None)
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            session = loop.run_until_complete(adapter.create_session(uuid4()))
            assert session.status == "failed"
            assert "No target project path" in session.error
        finally:
            loop.close()

    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_create_session_docker_failure(self, mock_run):
        mock_run.return_value = (1, "", "docker not found")

        adapter = SandboxedOpenCodeAdapter(target_project_path="/tmp/project")
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            session = loop.run_until_complete(adapter.create_session(uuid4()))
            assert session.status == "failed"
        finally:
            loop.close()


class TestSandboxFileOperations:
    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_write_protected_path_blocked(self, mock_run):
        mock_run.return_value = (0, "container_id", "")

        adapter = SandboxedOpenCodeAdapter(target_project_path="/tmp/project")
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            session = loop.run_until_complete(adapter.create_session(uuid4()))
            assert session.status == "active"

            result = loop.run_until_complete(adapter.write_file(session.session_id, "shared/config/laws.yaml", "hacked"))
            assert result is False
        finally:
            loop.close()

    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_read_protected_path_blocked(self, mock_run):
        mock_run.return_value = (0, "container_id", "")

        adapter = SandboxedOpenCodeAdapter(target_project_path="/tmp/project")
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            session = loop.run_until_complete(adapter.create_session(uuid4()))
            assert session.status == "active"

            result = loop.run_until_complete(adapter.read_file(session.session_id, ".env"))
            assert result is None
        finally:
            loop.close()


class TestSandboxBash:
    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_dangerous_command_blocked(self, mock_run):
        mock_run.return_value = (0, "container_id", "")

        adapter = SandboxedOpenCodeAdapter(target_project_path="/tmp/project")
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            session = loop.run_until_complete(adapter.create_session(uuid4()))
            assert session.status == "active"

            result = loop.run_until_complete(adapter.run_bash(session.session_id, "rm -rf /"))
            assert result["success"] is False
            assert "Dangerous command" in result["stderr"]
        finally:
            loop.close()


class TestSandboxExecute:
    @patch.object(SandboxedOpenCodeAdapter, "_run_cmd_async", new_callable=AsyncMock)
    def test_execute_blocks_protected_files(self, mock_run):
        mock_run.return_value = (0, "container_id", "")

        adapter = SandboxedOpenCodeAdapter(target_project_path="/tmp/project")
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            task_id = uuid4()
            result = loop.run_until_complete(adapter.execute(
                task_id=task_id,
                task_spec={
                    "files_to_create": ["shared/config/laws.yaml", "src/main.py"],
                    "files_to_modify": [],
                    "verification": "",
                },
                context={},
            ))
            assert "shared/config/laws.yaml" not in result.files_created
        finally:
            loop.close()
