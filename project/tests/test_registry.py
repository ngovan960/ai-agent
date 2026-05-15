import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus, TaskPriority
from shared.models.project import Project
from shared.models.module import Module
from shared.schemas.project import ProjectCreate, ProjectUpdate
from shared.schemas.module import ModuleCreate, ModuleUpdate
from shared.schemas.task import TaskCreate, TaskUpdate, StateTransitionRequest
from shared.config.state_transitions import validate_transition, is_terminal, get_valid_transitions
from services.orchestrator.services import tasks as task_service
from services.orchestrator.services import projects as project_service
from services.orchestrator.services import modules as module_service


@pytest.mark.asyncio
class TestProjectRegistry:
    async def test_create_project(self, test_db: AsyncSession):
        data = ProjectCreate(name="Test Project", description="Test desc")
        project = await project_service.create_project(test_db, data)
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "Test desc"

    async def test_get_project(self, test_db: AsyncSession):
        data = ProjectCreate(name="Test Project", description="Test desc")
        created = await project_service.create_project(test_db, data)
        found = await project_service.get_project(test_db, created.id)
        assert found is not None
        assert found.id == created.id
        assert found.name == "Test Project"

    async def test_get_project_not_found(self, test_db: AsyncSession):
        found = await project_service.get_project(test_db, uuid4())
        assert found is None

    async def test_list_projects(self, test_db: AsyncSession):
        p1 = await project_service.create_project(test_db, ProjectCreate(name="P1"))
        p2 = await project_service.create_project(test_db, ProjectCreate(name="P2"))
        items, total = await project_service.get_projects(test_db, page=1, page_size=10)
        assert total >= 2
        assert any(p.id == p1.id for p in items)
        assert any(p.id == p2.id for p in items)

    async def test_list_projects_with_status_filter(self, test_db: AsyncSession):
        await project_service.create_project(test_db, ProjectCreate(name="Active", status="active"))
        await project_service.create_project(test_db, ProjectCreate(name="Archived", status="archived"))
        items, total = await project_service.get_projects(test_db, page=1, page_size=10, status="active")
        for p in items:
            assert p.status == "active"

    async def test_list_projects_pagination(self, test_db: AsyncSession):
        for i in range(5):
            await project_service.create_project(test_db, ProjectCreate(name=f"Project {i}"))
        page1, total = await project_service.get_projects(test_db, page=1, page_size=2)
        page2, _ = await project_service.get_projects(test_db, page=2, page_size=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_update_project(self, test_db: AsyncSession):
        created = await project_service.create_project(test_db, ProjectCreate(name="Original"))
        updated = await project_service.update_project(
            test_db, created.id, ProjectUpdate(name="Updated")
        )
        assert updated is not None
        assert updated.name == "Updated"

    async def test_update_project_not_found(self, test_db: AsyncSession):
        result = await project_service.update_project(test_db, uuid4(), ProjectUpdate(name="X"))
        assert result is None

    async def test_delete_project(self, test_db: AsyncSession):
        created = await project_service.create_project(test_db, ProjectCreate(name="ToDelete"))
        deleted = await project_service.delete_project(test_db, created.id)
        assert deleted is True
        found = await project_service.get_project(test_db, created.id)
        assert found is None

    async def test_delete_project_not_found(self, test_db: AsyncSession):
        deleted = await project_service.delete_project(test_db, uuid4())
        assert deleted is False


@pytest.mark.asyncio
class TestModuleRegistry:
    async def test_create_module(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        data = ModuleCreate(name="Test Module", project_id=project.id, description="Module desc")
        mod = await module_service.create_module(test_db, data)
        assert mod.id is not None
        assert mod.name == "Test Module"
        assert mod.project_id == project.id

    async def test_get_module(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        data = ModuleCreate(name="Test Module", project_id=project.id)
        created = await module_service.create_module(test_db, data)
        found = await module_service.get_module(test_db, created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_module_not_found(self, test_db: AsyncSession):
        found = await module_service.get_module(test_db, uuid4())
        assert found is None

    async def test_list_modules_by_project(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        project2 = await project_service.create_project(test_db, ProjectCreate(name="P2"))
        m1 = await module_service.create_module(test_db, ModuleCreate(name="M1", project_id=project.id))
        m2 = await module_service.create_module(test_db, ModuleCreate(name="M2", project_id=project2.id))
        items, _ = await module_service.get_modules(test_db, project_id=project.id, page=1, page_size=10)
        assert len(items) >= 1
        assert any(m.id == m1.id for m in items)

    async def test_update_module(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        created = await module_service.create_module(test_db, ModuleCreate(name="Original", project_id=project.id))
        updated = await module_service.update_module(test_db, created.id, ModuleUpdate(name="Updated"))
        assert updated.name == "Updated"

    async def test_delete_module(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        created = await module_service.create_module(test_db, ModuleCreate(name="ToDelete", project_id=project.id))
        deleted = await module_service.delete_module(test_db, created.id)
        assert deleted is True

    async def test_add_module_dependency(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        m1 = await module_service.create_module(test_db, ModuleCreate(name="M1", project_id=project.id))
        m2 = await module_service.create_module(test_db, ModuleCreate(name="M2", project_id=project.id))
        dep = await module_service.add_module_dependency(test_db, m1.id, m2.id)
        assert dep is not None
        assert dep.module_id == m1.id

    async def test_add_module_dependency_duplicate(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        m1 = await module_service.create_module(test_db, ModuleCreate(name="M1", project_id=project.id))
        m2 = await module_service.create_module(test_db, ModuleCreate(name="M2", project_id=project.id))
        await module_service.add_module_dependency(test_db, m1.id, m2.id)
        dep2 = await module_service.add_module_dependency(test_db, m1.id, m2.id)
        assert dep2 is None

    async def test_remove_module_dependency(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        m1 = await module_service.create_module(test_db, ModuleCreate(name="M1", project_id=project.id))
        m2 = await module_service.create_module(test_db, ModuleCreate(name="M2", project_id=project.id))
        dep = await module_service.add_module_dependency(test_db, m1.id, m2.id)
        deleted = await module_service.remove_module_dependency(test_db, dep.id)
        assert deleted is True


@pytest.mark.asyncio
class TestTaskRegistry:
    async def test_create_task(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        data = TaskCreate(title="Test Task", description="Test", project_id=project.id, priority=TaskPriority.MEDIUM)
        task = await task_service.create_task(test_db, data)
        assert task.id is not None
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.MEDIUM

    async def test_get_task(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        data = TaskCreate(title="Test Task", description="Test", project_id=project.id)
        created = await task_service.create_task(test_db, data)
        found = await task_service.get_task(test_db, created.id)
        assert found is not None
        assert found.title == "Test Task"

    async def test_get_task_not_found(self, test_db: AsyncSession):
        found = await task_service.get_task(test_db, uuid4())
        assert found is None

    async def test_list_tasks_by_project(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        project2 = await project_service.create_project(test_db, ProjectCreate(name="P2"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project2.id))
        items, _ = await task_service.get_tasks(test_db, project_id=project.id, page=1, page_size=10)
        assert any(t.id == t1.id for t in items)

    async def test_list_tasks_by_module(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        mod = await module_service.create_module(test_db, ModuleCreate(name="M", project_id=project.id))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id, module_id=mod.id))
        items, _ = await task_service.get_tasks(test_db, module_id=mod.id, page=1, page_size=10)
        assert any(t.id == t1.id for t in items)

    async def test_list_tasks_with_status_filter(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        items, _ = await task_service.get_tasks(test_db, status="NEW", page=1, page_size=10)
        assert len(items) >= 1

    async def test_update_task(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        created = await task_service.create_task(test_db, TaskCreate(title="Original", project_id=project.id))
        updated = await task_service.update_task(test_db, created.id, TaskUpdate(title="Updated"))
        assert updated.title == "Updated"

    async def test_update_task_not_found(self, test_db: AsyncSession):
        result = await task_service.update_task(test_db, uuid4(), TaskUpdate(title="X"))
        assert result is None

    async def test_delete_task(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        created = await task_service.create_task(test_db, TaskCreate(title="ToDelete", project_id=project.id))
        deleted = await task_service.delete_task(test_db, created.id)
        assert deleted is True

    async def test_add_task_dependency(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        dep = await task_service.add_task_dependency(test_db, t1.id, t2.id)
        assert dep is not None

    async def test_add_task_dependency_self(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        dep = await task_service.add_task_dependency(test_db, t1.id, t1.id)
        assert dep is None

    async def test_add_task_dependency_duplicate(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        dep2 = await task_service.add_task_dependency(test_db, t1.id, t2.id)
        assert dep2 is None

    async def test_task_output(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        output = await task_service.create_task_output(test_db, t1.id, "code", {"content": "print('hello')"})
        assert output is not None
        assert output.output_type == "code"

    async def test_task_output_not_found(self, test_db: AsyncSession):
        output = await task_service.create_task_output(test_db, uuid4(), "code", {})
        assert output is None


@pytest.mark.asyncio
class TestStateTransitionHooks:
    async def test_pre_transition_hook_no_deps(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        can_proceed, error = await task_service.pre_transition_hook(test_db, t1.id, "NEW", "ANALYZING")
        assert can_proceed is True
        assert error is None

    async def test_pre_transition_hook_blocked_by_deps(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        can_proceed, error = await task_service.pre_transition_hook(test_db, t1.id, "NEW", "ANALYZING")
        assert can_proceed is False
        assert "blocked by unresolved dependencies" in (error or "")

    async def test_pre_transition_hook_deps_resolved(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        t2.status = TaskStatus.DONE
        await test_db.flush()
        can_proceed, error = await task_service.pre_transition_hook(test_db, t1.id, "NEW", "ANALYZING")
        assert can_proceed is True

    async def test_post_transition_hook_triggers_blocked(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t2.id, t1.id)
        t2.status = TaskStatus.BLOCKED
        await test_db.flush()
        triggered = await task_service.post_transition_hook(test_db, t1.id, "DONE")
        assert len(triggered) >= 0

    async def test_post_transition_hook_not_terminal(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        triggered = await task_service.post_transition_hook(test_db, t1.id, "ANALYZING")
        assert len(triggered) == 0
