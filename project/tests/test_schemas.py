import pytest
from uuid import uuid4

from shared.schemas.project import ProjectCreate, ProjectUpdate
from shared.schemas.module import ModuleCreate, ModuleUpdate
from shared.schemas.task import TaskCreate, TaskUpdate, StateTransitionRequest
from shared.models.project import ProjectStatus
from shared.models.module import ModuleStatus
from shared.models.task import TaskStatus, TaskPriority, RiskLevel


class TestProjectSchemas:
    def test_project_create_valid(self):
        data = ProjectCreate(name="Test Project", description="A test project")
        assert data.name == "Test Project"
        assert data.description == "A test project"
        assert data.tech_stack == []

    def test_project_create_with_tech_stack(self):
        data = ProjectCreate(name="Test", tech_stack=["Python", "FastAPI"])
        assert data.tech_stack == ["Python", "FastAPI"]

    def test_project_create_name_required(self):
        with pytest.raises(Exception):
            ProjectCreate()

    def test_project_update_partial(self):
        data = ProjectUpdate(status=ProjectStatus.PAUSED)
        assert data.status == ProjectStatus.PAUSED
        assert data.name is None

    def test_project_update_all_fields(self):
        data = ProjectUpdate(
            name="Updated",
            description="New desc",
            status=ProjectStatus.COMPLETED,
            tech_stack=["React"],
            architecture="monolith",
            rules={"key": "value"},
        )
        assert data.name == "Updated"
        assert data.rules == {"key": "value"}


class TestModuleSchemas:
    def test_module_create_valid(self):
        project_id = uuid4()
        data = ModuleCreate(name="Auth Module", project_id=project_id)
        assert data.name == "Auth Module"
        assert data.project_id == project_id

    def test_module_update_status(self):
        data = ModuleUpdate(status=ModuleStatus.IN_PROGRESS)
        assert data.status == ModuleStatus.IN_PROGRESS


class TestTaskSchemas:
    def test_task_create_valid(self):
        project_id = uuid4()
        data = TaskCreate(
            title="Implement login",
            project_id=project_id,
            priority=TaskPriority.HIGH,
        )
        assert data.title == "Implement login"
        assert data.priority == TaskPriority.HIGH
        assert data.max_retries == 2

    def test_task_create_with_module(self):
        project_id = uuid4()
        module_id = uuid4()
        data = TaskCreate(title="Task", project_id=project_id, module_id=module_id)
        assert data.module_id == module_id

    def test_task_update_priority(self):
        data = TaskUpdate(priority=TaskPriority.HIGH)
        assert data.priority == TaskPriority.HIGH
        assert not hasattr(data, "status")

    def test_task_update_confidence_bounds(self):
        data = TaskUpdate(confidence=0.85)
        assert data.confidence == 0.85

    def test_state_transition_request(self):
        data = StateTransitionRequest(
            target_status=TaskStatus.DONE,
            reason="All checks passed",
        )
        assert data.target_status == TaskStatus.DONE
        assert data.reason == "All checks passed"
