from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from shared.models.project import Project, ProjectStatus
from shared.models.task import TaskStatus
from shared.schemas.project import ProjectCreate


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    return db


@pytest.fixture
def sample_project():
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        status=ProjectStatus.ACTIVE,
        tech_stack=["Python", "FastAPI"],
    )


class TestProjectService:
    @pytest.mark.asyncio
    async def test_create_project(self, mock_db, sample_project):
        from services.orchestrator.services.projects import create_project

        data = ProjectCreate(name="Test Project", description="A test project")
        mock_db.refresh = AsyncMock(side_effect=lambda x: None)

        await create_project(mock_db, data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()


class TestStateTransitions:
    def test_terminal_states_are_correct(self):
        assert TaskStatus.DONE.value in {"DONE", "FAILED", "CANCELLED"}
        assert TaskStatus.FAILED.value in {"DONE", "FAILED", "CANCELLED"}
        assert TaskStatus.CANCELLED.value in {"DONE", "FAILED", "CANCELLED"}

    def test_non_terminal_states(self):
        assert TaskStatus.NEW.value not in {"DONE", "FAILED", "CANCELLED"}
        assert TaskStatus.ANALYZING.value not in {"DONE", "FAILED", "CANCELLED"}
        assert TaskStatus.PLANNING.value not in {"DONE", "FAILED", "CANCELLED"}
        assert TaskStatus.IMPLEMENTING.value not in {"DONE", "FAILED", "CANCELLED"}
