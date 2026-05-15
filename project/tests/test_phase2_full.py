import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskStatus
from shared.schemas.task import TaskCreate
from services.orchestrator.services import tasks as task_service
from services.orchestrator.services import projects as project_service
from services.orchestrator.services import dependency_service
from shared.schemas.project import ProjectCreate


@pytest.mark.asyncio
class TestDependencyManagement:
    async def test_can_start_no_deps(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        can, blocked = await dependency_service.can_start(test_db, t1.id)
        assert can is True
        assert len(blocked) == 0

    async def test_can_start_with_undone_deps(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        can, blocked = await dependency_service.can_start(test_db, t1.id)
        assert can is False
        assert t2.id in blocked

    async def test_can_start_with_done_deps(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        t2.status = TaskStatus.DONE
        await test_db.flush()
        can, blocked = await dependency_service.can_start(test_db, t1.id)
        assert can is True

    async def test_build_dependency_graph(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        t3 = await task_service.create_task(test_db, TaskCreate(title="T3", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        await task_service.add_task_dependency(test_db, t1.id, t3.id)
        graph = await dependency_service.build_dependency_graph(test_db, [t1.id, t2.id, t3.id])
        assert t1.id in graph
        assert len(graph[t1.id]) == 2
        assert t2.id in graph[t1.id]
        assert t3.id in graph[t1.id]

    async def test_has_circular_dependency_none(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        t3 = await task_service.create_task(test_db, TaskCreate(title="T3", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        has_cycle, cycle = await dependency_service.has_circular_dependency(
            test_db, t3.id, [t1.id]
        )
        assert has_cycle is False

    async def test_has_circular_dependency_direct(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t1.id)
        has_cycle, cycle = await dependency_service.has_circular_dependency(
            test_db, t1.id, [t1.id]
        )
        assert has_cycle is True
        assert cycle is not None

    async def test_get_task_dependencies(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        deps = await dependency_service.get_task_dependencies(test_db, t1.id)
        assert len(deps) >= 1
        assert deps[0]["task_id"] == str(t2.id)

    async def test_get_dependent_tasks(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t2 = await task_service.create_task(test_db, TaskCreate(title="T2", project_id=project.id))
        await task_service.add_task_dependency(test_db, t1.id, t2.id)
        dependents = await dependency_service.get_dependent_tasks(test_db, t2.id)
        assert len(dependents) >= 1
        assert dependents[0]["task_id"] == str(t1.id)


@pytest.mark.asyncio
class TestEscalation:
    async def test_should_escalate_exceeded_retries(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t1.retries = 3
        await test_db.flush()
        from services.orchestrator.services import escalation_service
        should, reason = await escalation_service.should_escalate(test_db, t1.id)
        assert should is True

    async def test_should_not_escalate_low_retries(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        from services.orchestrator.services import escalation_service
        should, reason = await escalation_service.should_escalate(test_db, t1.id)
        assert should is False

    async def test_escalate_task(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        from services.orchestrator.services import escalation_service
        success, msg = await escalation_service.escalate_task(test_db, t1.id, "Test escalation")
        assert success is True

    async def test_escalate_already_escalated(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(title="T1", project_id=project.id))
        t1.status = TaskStatus.ESCALATED
        await test_db.flush()
        from services.orchestrator.services import escalation_service
        success, msg = await escalation_service.escalate_task(test_db, t1.id, "Test")
        assert success is False

    async def test_priority_queue_push_pop(self):
        from services.orchestrator.services.escalation_service import EscalationPriorityQueue, EscalationItem
        q = EscalationPriorityQueue()
        q.push(EscalationItem(task_id=uuid4(), task_title="Medium", risk_level="medium", priority=0))
        q.push(EscalationItem(task_id=uuid4(), task_title="Critical", risk_level="critical", priority=0))
        q.push(EscalationItem(task_id=uuid4(), task_title="Low", risk_level="low", priority=0))
        first = q.pop()
        assert first is not None
        assert first.risk_level == "critical"
        second = q.pop()
        assert second.risk_level == "medium"

    async def test_priority_queue_empty(self):
        from services.orchestrator.services.escalation_service import EscalationPriorityQueue
        q = EscalationPriorityQueue()
        assert q.pop() is None
        assert q.is_empty() is True

    async def test_get_escalation_stats(self, test_db: AsyncSession):
        from services.orchestrator.services import escalation_service
        stats = await escalation_service.get_escalation_stats(test_db)
        assert "queue_size" in stats
        assert "total_escalated_tasks" in stats


@pytest.mark.asyncio
class TestMentorTakeover:
    async def test_mentor_rewrite(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(
            title="T1", project_id=project.id, status=TaskStatus.ESCALATED,
        ))
        from services.orchestrator.services.mentor_service import mentor_takeover, MentorAction
        success, msg, result = await mentor_takeover(
            test_db, t1.id, "mentor-1", MentorAction.REWRITE, "Bug in logic"
        )
        assert success is True
        assert result is not None
        assert result["action"] == "rewrite"

    async def test_mentor_redesign(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(
            title="T1", project_id=project.id, status=TaskStatus.ESCALATED,
        ))
        from services.orchestrator.services.mentor_service import mentor_takeover, MentorAction
        success, msg, result = await mentor_takeover(
            test_db, t1.id, "mentor-1", MentorAction.REDESIGN, "Architecture broken"
        )
        assert success is True

    async def test_mentor_reject(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(
            title="T1", project_id=project.id, status=TaskStatus.ESCALATED,
        ))
        from services.orchestrator.services.mentor_service import mentor_takeover, MentorAction
        success, msg, result = await mentor_takeover(
            test_db, t1.id, "mentor-1", MentorAction.REJECT, "Not feasible"
        )
        assert success is True
        assert result["action"] == "reject"

    async def test_mentor_task_not_found(self, test_db: AsyncSession):
        from services.orchestrator.services.mentor_service import mentor_takeover, MentorAction
        success, msg, result = await mentor_takeover(
            test_db, uuid4(), "mentor-1", MentorAction.REWRITE, "Test"
        )
        assert success is False

    async def test_check_mentor_quota(self, test_db: AsyncSession):
        from services.orchestrator.services.mentor_service import check_mentor_quota
        can_call, remaining, limit = await check_mentor_quota(test_db)
        assert can_call is True
        assert remaining >= 0

    async def test_record_mentor_call(self, test_db: AsyncSession):
        from services.orchestrator.services.mentor_service import check_mentor_quota, record_mentor_call
        before_can, before_rem, limit = await check_mentor_quota(test_db)
        await record_mentor_call(test_db)
        after_can, after_rem, _ = await check_mentor_quota(test_db)
        assert after_rem == before_rem - 1

    async def test_get_mentor_instructions(self, test_db: AsyncSession):
        project = await project_service.create_project(test_db, ProjectCreate(name="P"))
        t1 = await task_service.create_task(test_db, TaskCreate(
            title="T1", project_id=project.id, status=TaskStatus.ESCALATED,
        ))
        from services.orchestrator.services.mentor_service import mentor_takeover, MentorAction, get_mentor_instructions
        await mentor_takeover(test_db, t1.id, "mentor-1", MentorAction.REWRITE, "Test")
        instructions = await get_mentor_instructions(test_db, t1.id)
        assert len(instructions) >= 1
        assert instructions[0]["instruction_type"] == "rewrite"


@pytest.mark.asyncio
class TestValidationNode:
    async def test_should_skip_validation_low_trivial(self):
        from services.orchestrator.services import validation as validation_service
        assert validation_service.should_skip_validation("low", "trivial") is True

    async def test_should_skip_validation_low_simple(self):
        from services.orchestrator.services import validation as validation_service
        assert validation_service.should_skip_validation("low", "simple") is True

    async def test_should_not_skip_validation_medium(self):
        from services.orchestrator.services import validation as validation_service
        assert validation_service.should_skip_validation("medium", "trivial") is False

    async def test_should_not_skip_validation_high(self):
        from services.orchestrator.services import validation as validation_service
        assert validation_service.should_skip_validation("high", "trivial") is False

    async def test_validate_classification(self):
        from services.orchestrator.services import validation as validation_service
        from shared.schemas.validation import ValidationRequest, GatekeeperClassification, TaskType, RiskLevel, Complexity, ValidationVerdict
        request = ValidationRequest(
            user_request="Fix login bug",
            gatekeeper_classification=GatekeeperClassification(
                task_type=TaskType.BUG_FIX,
                complexity=Complexity.SIMPLE,
                risk_level=RiskLevel.LOW,
                effort="small",
                estimated_effort="2h",
                reasoning="This is a simple bug fix",
                confidence=0.9,
            ),
        )
        response = validation_service.validate_classification(request)
        assert response.verdict in (ValidationVerdict.APPROVED, ValidationVerdict.REJECTED)
        assert 0 <= response.confidence <= 1
