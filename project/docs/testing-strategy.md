# Testing Strategy - AI SDLC System

## Tài liệu Chiến lược Kiểm thử

---

## 1. Tổng quan

Tài liệu này định nghĩa chiến lược kiểm thử toàn diện cho AI SDLC System. Testing coverage mục tiêu **>80%**, bao gồm unit tests, integration tests, end-to-end tests, và các test đặc thù cho state machine, LLM agents, và workflow.

### 1.1 Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E ╲           ~5% tests
                 ╱  Tests  ╲         End-to-end workflow
                ╱────────────╲
               ╱                ╲
              ╱   Integration    ╲   ~25% tests
             ╱     Tests         ╲  Database, API, State Machine
            ╱────────────────────╲
           ╱                      ╲
          ╱      Unit Tests        ╲ ~70% tests
         ╱   (pytest, mocking)       ╲ Models, Services, Utils
        ╱──────────────────────────────╲
```

| Level | Tỉ lệ | Số lượng ước tính | Focus |
|-------|--------|-------------------|-------|
| Unit | ~70% | ~350 tests | Business logic, state machine, LLM call, cost calc |
| Integration | ~25% | ~125 tests | API endpoints, DB operations, state machine transitions |
| E2E | ~5% | ~25 tests | Full workflow, agent coordination |

### 1.2 Tech Stack

| Tool | Phiên bản | Mục đích |
|------|-----------|----------|
| pytest | 8.x | Test runner và framework |
| httpx | 0.27+ | Async HTTP client cho API testing |
| pytest-asyncio | 0.23+ | Async test support |
| SQLAlchemy | 2.0+ | ORM và database operations |
| asyncpg | 0.29+ | Async PostgreSQL driver |
| testcontainers | 3.x | Docker containers cho integration tests |
| faker | 28+ | Fake data generation |
| freezegun | 1.x | Time mocking |
| respx | 0.21+ | HTTP request mocking |
| pytest-cov | 5+ | Coverage reporting |
| pytest-xdist | 3+ | Parallel test execution |
| pytest-timeout | 2+ | Test timeout enforcement |

---

## 2. Unit Testing với pytest

### 2.1 Cấu trúc Test Directory

```
tests/
├── unit/
│   ├── __init__.py
│   ├── conftest.py                    # Shared unit test fixtures
│   ├── models/
│   │   ├── test_task.py
│   │   ├── test_project.py
│   │   ├── test_module_spec.py
│   │   ├── test_user.py
│   │   ├── test_api_key.py
│   │   └── test_cost_tracking.py
│   ├── services/
│   │   ├── test_state_machine.py      # State transition logic
│   │   ├── test_workflow_engine.py
│   │   ├── test_llm_gateway.py
│   │   ├── test_model_router.py
│   │   ├── test_context_builder.py
│   │   ├── test_prompt_renderer.py
│   │   ├── test_cost_calculator.py
│   │   ├── test_circuit_breaker.py
│   │   └── test_auth_service.py
│   ├── agents/
│   │   ├── test_gatekeeper.py
│   │   ├── test_orchestrator.py
│   │   ├── test_specialist.py
│   │   ├── test_auditor.py
│   │   ├── test_mentor.py
│   │   └── test_monitoring.py
│   └── utils/
│       ├── test_validators.py
│       ├── test_sanitizers.py
│       └── test_crypto.py
├── integration/
│   ├── __init__.py
│   ├── conftest.py                    # Integration test fixtures
│   ├── api/
│   │   ├── test_auth_endpoints.py
│   │   ├── test_project_endpoints.py
│   │   ├── test_module_endpoints.py
│   │   ├── test_task_endpoints.py
│   │   ├── test_workflow_endpoints.py
│   │   ├── test_audit_log_endpoints.py
│   │   ├── test_cost_stats_endpoints.py
│   │   └── test_health_endpoint.py
│   ├── db/
│   │   ├── test_repositories.py
│   │   ├── test_migrations.py
│   │   └── test_constraints.py
│   └── state_machine/
│       ├── test_all_transitions.py
│       ├── test_concurrent_transitions.py
│       └── test_terminal_states.py
├── e2e/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_full_workflow.py
│   ├── test_agent_coordination.py
│   └── test_error_scenarios.py
└── conftest.py                        # Global fixtures
```

### 2.2 Test Naming Conventions

```python
# Format: test_{unit}_{scenario}_{expected_result}

# Ví dụ:
def test_state_machine_transition_from_new_to_analyzing_succeeds():
    ...

def test_state_machine_transition_from_done_to_implementing_fails():
    ...

def test_cost_calculator_with_deepseek_v4_flash_returns_correct_cost():
    ...

def test_llm_gateway_circuit_breaker_opens_after_five_failures():
    ...

def test_task_create_with_missing_title_returns_validation_error():
    ...
```

**Quy ước đặt tên:**

| Pattern | Mô tả | Ví dụ |
|---------|--------|-------|
| `test_{method}_{scenario}_succeeds` | Happy path | `test_transition_valid_state_succeeds` |
| `test_{method}_{scenario}_fails` | Error path | `test_transition_invalid_state_fails` |
| `test_{method}_{scenario}_returns_{result}` | Specific result | `test_cost_calc_deepseek_flash_returns_correct` |
| `test_{method}_{scenario}_raises_{exception}` | Exception case | `test_create_user_duplicate_raises_conflict` |
| `test_{method}_when_{condition}` | Conditional | `test_transition_when_blocked_dependency_fails` |

### 2.3 Unit Test Ví dụ - State Machine

```python
# tests/unit/services/test_state_machine.py
import pytest
from app.services.state_machine import StateMachine, InvalidTransitionError
from app.models.task import Task

class TestStateMachineValidTransitions:
    def test_transition_from_new_to_analyzing_succeeds(self, state_machine):
        result = state_machine.transition(
            task_id="task-uuid",
            from_state="NEW",
            to_state="ANALYZING",
            reason="Gatekeeper classified task",
            actor="gatekeeper",
        )
        assert result.success is True
        assert result.new_state == "ANALYZING"

    def test_transition_from_analyzing_to_planning_succeeds(self, state_machine):
        result = state_machine.transition(
            task_id="task-uuid",
            from_state="ANALYZING",
            to_state="PLANNING",
            reason="Orchestrator created plan",
            actor="orchestrator",
        )
        assert result.success is True

    def test_transition_from_implementing_to_verifying_succeeds(self, state_machine):
        result = state_machine.transition(
            task_id="task-uuid",
            from_state="IMPLEMENTING",
            to_state="VERIFYING",
            reason="Code complete, entering sandbox",
            actor="specialist",
        )
        assert result.success is True

    def test_all_18_valid_transitions_succeed(self, state_machine):
        """Test tất cả 18 transitions hợp lệ."""
        valid_transitions = [
            ("NEW", "ANALYZING"),
            ("NEW", "BLOCKED"),
            ("ANALYZING", "PLANNING"),
            ("ANALYZING", "BLOCKED"),
            ("ANALYZING", "CANCELLED"),
            ("PLANNING", "IMPLEMENTING"),
            ("PLANNING", "BLOCKED"),
            ("PLANNING", "CANCELLED"),
            ("IMPLEMENTING", "VERIFYING"),
            ("IMPLEMENTING", "BLOCKED"),
            ("IMPLEMENTING", "FAILED"),
            ("VERIFYING", "REVIEWING"),
            ("VERIFYING", "IMPLEMENTING"),
            ("VERIFYING", "FAILED"),
            ("REVIEWING", "DONE"),
            ("REVIEWING", "IMPLEMENTING"),
            ("REVIEWING", "ESCALATED"),
            ("REVIEWING", "CANCELLED"),
            ("ESCALATED", "PLANNING"),
            ("ESCALATED", "FAILED"),
            ("BLOCKED", "PLANNING"),
            ("BLOCKED", "CANCELLED"),
        ]
        for from_state, to_state in valid_transitions:
            result = state_machine.transition(
                task_id="task-uuid",
                from_state=from_state,
                to_state=to_state,
                reason="Test transition",
                actor="test",
            )
            assert result.success is True, f"Failed: {from_state} → {to_state}"


class TestStateMachineInvalidTransitions:
    def test_transition_from_done_to_implementing_fails(self, state_machine):
        with pytest.raises(InvalidTransitionError) as exc_info:
            state_machine.transition(
                task_id="task-uuid",
                from_state="DONE",
                to_state="IMPLEMENTING",
                reason="Invalid transition attempt",
                actor="test",
            )
        assert "terminal state" in str(exc_info.value).lower()

    def test_transition_from_failed_to_any_fails(self, state_machine):
        for target in ["NEW", "ANALYZING", "PLANNING", "IMPLEMENTING", "DONE"]:
            with pytest.raises(InvalidTransitionError):
                state_machine.transition(
                    task_id="task-uuid",
                    from_state="FAILED",
                    to_state=target,
                    reason="Invalid",
                    actor="test",
                )

    def test_transition_from_cancelled_to_any_fails(self, state_machine):
        with pytest.raises(InvalidTransitionError):
            state_machine.transition(
                task_id="task-uuid",
                from_state="CANCELLED",
                to_state="IMPLEMENTING",
                reason="Invalid",
                actor="test",
            )

    def test_transition_from_verifying_to_planning_fails(self, state_machine):
        with pytest.raises(InvalidTransitionError):
            state_machine.transition(
                task_id="task-uuid",
                from_state="VERIFYING",
                to_state="PLANNING",
                reason="Invalid",
                actor="test",
            )

    def test_transition_from_reviewing_to_planning_fails(self, state_machine):
        with pytest.raises(InvalidTransitionError):
            state_machine.transition(
                task_id="task-uuid",
                from_state="REVIEWING",
                to_state="PLANNING",
                reason="Invalid",
                actor="test",
            )

    def test_all_22_invalid_transitions_fail(self, state_machine):
        """Test tất cả 22 transitions không hợp lệ."""
        invalid_transitions = [
            ("DONE", "ANY"),
            ("FAILED", "ANY"),
            ("CANCELLED", "ANY"),
            ("VERIFYING", "PLANNING"),
            ("REVIEWING", "PLANNING"),
            ("REVIEWING", "VERIFYING"),
            ("ESCALATED", "IMPLEMENTING"),
            ("ESCALATED", "VERIFYING"),
            ("ESCALATED", "REVIEWING"),
            ("BLOCKED", "IMPLEMENTING"),
            ("BLOCKED", "VERIFYING"),
            ("NEW", "DONE"),
        ]
        # ... test từng transition


class TestStateMachineEscalatedDoneRule:
    def test_escalated_to_done_with_verified_output_succeeds(self, state_machine):
        """LAW-009 Exception: ESCALATED → DONE chỉ khi đã verified."""
        result = state_machine.transition(
            task_id="task-uuid",
            from_state="ESCALATED",
            to_state="DONE",
            reason="Mentor approves, verification passed",
            actor="mentor",
            metadata={"verification_passed": True},
        )
        assert result.success is True

    def test_escalated_to_done_without_verification_fails(self, state_machine):
        """ESCALATED → DONE không cho phép nếu chưa verified."""
        with pytest.raises(InvalidTransitionError):
            state_machine.transition(
                task_id="task-uuid",
                from_state="ESCALATED",
                to_state="DONE",
                reason="Mentor bypass",
                actor="mentor",
                metadata={"verification_passed": False},
            )


class TestStateMachineRetryTracking:
    def test_retry_count_increments_on_reviewing_to_implementing(self, state_machine):
        result = state_machine.transition(
            task_id="task-uuid",
            from_state="REVIEWING",
            to_state="IMPLEMENTING",
            reason="Auditor requests revision",
            actor="auditor",
        )
        assert result.retry_count == 1

    def test_max_retries_exceeded_triggers_escalation(self, state_machine):
        state_machine.transition("task-uuid", "REVIEWING", "IMPLEMENTING", ...)
        state_machine.transition("task-uuid", "IMPLEMENTING", "VERIFYING", ...)
        state_machine.transition("task-uuid", "VERIFYING", "REVIEWING", ...)
        result = state_machine.transition(
            "task-uuid", "REVIEWING", "IMPLEMENTING", ...
        )
        assert result.retry_count == 2

        # Retry count > 2 should force ESCALATED
        with pytest.raises(MaxRetryExceededError):
            state_machine.transition(
                "task-uuid", "REVIEWING", "IMPLEMENTING", ...
            )
```

### 2.4 Unit Test Ví dụ - Cost Calculator

```python
# tests/unit/services/test_cost_calculator.py
import pytest
from app.services.cost_calculator import calculate_cost, PRICING_TABLE

class TestCostCalculator:
    def test_calculate_cost_deepseek_v4_flash(self):
        cost = calculate_cost("deepseek-v4-flash", input_tokens=1000, output_tokens=500)
        expected = (1000 / 1_000_000 * 0.10) + (500 / 1_000_000 * 0.30)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_deepseek_v4_pro(self):
        cost = calculate_cost("deepseek-v4-pro", input_tokens=8000, output_tokens=2000)
        expected = (8000 / 1_000_000 * 0.50) + (2000 / 1_000_000 * 1.50)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_qwen_3_5_plus(self):
        cost = calculate_cost("qwen-3.5-plus", input_tokens=5000, output_tokens=1000)
        expected = (5000 / 1_000_000 * 0.30) + (1000 / 1_000_000 * 0.90)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_qwen_3_6_plus(self):
        cost = calculate_cost("qwen-3.6-plus", input_tokens=16000, output_tokens=4000)
        expected = (16000 / 1_000_000 * 0.80) + (4000 / 1_000_000 * 2.40)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            calculate_cost("gpt-4", input_tokens=100, output_tokens=50)

    def test_calculate_cost_zero_tokens(self):
        cost = calculate_cost("deepseek-v4-flash", input_tokens=0, output_tokens=0)
        assert cost == 0.0
```

### 2.5 Unit Test Ví dụ - Circuit Breaker

```python
# tests/unit/services/test_circuit_breaker.py
import pytest
from app.services.circuit_breaker import CircuitBreaker, CircuitState

class TestCircuitBreaker:
    def test_circuit_starts_closed(self, circuit_breaker):
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold_failures(self, circuit_breaker):
        for _ in range(5):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN

    def test_circuit_remains_closed_under_threshold(self, circuit_breaker):
        for _ in range(4):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_circuit_transitions_to_half_open_after_timeout(self, circuit_breaker, freezer):
        for _ in range(5):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN

        freezer.move_to(datetime.now() + timedelta(seconds=30))
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_circuit_closes_after_successful_probe(self, circuit_breaker):
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_circuit_reopens_after_failed_probe(self, circuit_breaker):
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN

    def test_circuit_rejects_requests_when_open(self, circuit_breaker):
        circuit_breaker.state = CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            circuit_breaker.execute(lambda: "should not run")
```

---

## 3. Integration Testing với Test Database

### 3.1 Test Database Setup

```python
# tests/integration/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from alembic import command
from alembic.config import Config

from app.models.base import Base
from app.db.session import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ai_sdlc:test@localhost:5432/ai_sdlc_test"
)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="session")
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture(autouse=True)
async def clean_tables(db_session):
    """Xoá data trong tất cả tables sau mỗi test."""
    yield
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()
```

### 3.2 Integration Test Ví dụ - Repository

```python
# tests/integration/db/test_repositories.py
import pytest
from app.repositories.task_repository import TaskRepository
from app.models.task import Task

class TestTaskRepository:
    @pytest.fixture
    def task_repo(self, db_session):
        return TaskRepository(db_session)

    async def test_create_task(self, task_repo, db_session):
        project = await self._create_project(db_session)
        module = await self._create_module(db_session, project.id)

        task = await task_repo.create(
            module_id=module.id,
            title="Implement auth module",
            description="Create login/register/logout endpoints",
            priority="HIGH",
        )

        assert task.id is not None
        assert task.state == "NEW"
        assert task.retry_count == 0
        assert task.max_retries == 2

    async def test_get_task_by_id(self, task_repo, db_session):
        project = await self._create_project(db_session)
        module = await self._create_module(db_session, project.id)
        created = await task_repo.create(
            module_id=module.id,
            title="Test task",
            priority="MEDIUM",
        )

        found = await task_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.title == "Test task"

    async def test_list_tasks_with_filter(self, task_repo, db_session):
        project = await self._create_project(db_session)
        module = await self._create_module(db_session, project.id)

        await task_repo.create(module_id=module.id, title="Task 1", priority="HIGH")
        await task_repo.create(module_id=module.id, title="Task 2", priority="LOW")

        tasks = await task_repo.list(
            module_id=module.id,
            priority="HIGH",
        )

        assert len(tasks) == 1
        assert tasks[0].priority == "HIGH"

    async def test_update_task_state(self, task_repo, db_session):
        project = await self._create_project(db_session)
        module = await self._create_module(db_session, project.id)
        task = await task_repo.create(
            module_id=module.id, title="Test task", priority="MEDIUM"
        )

        updated = await task_repo.update_state(
            task_id=task.id,
            new_state="ANALYZING",
            reason="Gatekeeper classified",
            actor="gatekeeper",
        )

        assert updated.state == "ANALYZING"
        assert updated.updated_at > task.created_at
```

### 3.3 Integration Test Ví dụ - Database Constraints

```python
# tests/integration/db/test_constraints.py
import pytest
from sqlalchemy.exc import IntegrityError

class TestDatabaseConstraints:
    async def test_task_state_check_constraint(self, db_session):
        """Verify state enum constraint."""
        with pytest.raises(IntegrityError):
            await db_session.execute(
                text("INSERT INTO tasks (id, module_id, title, state) "
                     "VALUES (gen_random_uuid(), :mid, 'Test', 'INVALID_STATE')")
            )

    async def test_state_transition_audit_required(self, db_session):
        """Verify audit log required cho state transitions."""
        # ... test that every state transition creates audit log

    async def test_api_key_unique_prefix_constraint(self, db_session):
        """Verify API key prefix uniqueness."""
        # ... test unique constraint on key_prefix

    async def test_cost_tracking_unique_constraint(self, db_session):
        """Verify cost_tracking unique on (project_id, task_id, date, model)."""
        # ... test upsert behavior
```

---

## 4. API Testing với httpx TestClient

### 4.1 FastAPI Test Client Setup

```python
# tests/integration/api/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
async def auth_headers(client, db_session):
    """Tạo authenticated headers cho test."""
    user = await create_test_user(db_session, role="admin")
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def api_key_headers(client, db_session):
    """Tạo API key headers cho agent test."""
    api_key = await create_test_api_key(db_session, agent="specialist")
    return {"X-API-Key": api_key.raw_key}
```

### 4.2 API Test Ví dụ - Auth Endpoints

```python
# tests/integration/api/test_auth_endpoints.py
class TestLoginEndpoint:
    async def test_login_success(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "username": "testadmin",
            "password": "TestP@ss1!",
        })
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 900

    async def test_login_invalid_password(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "username": "testadmin",
            "password": "wrong_password",
        })
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_001"

    async def test_login_rate_limiting(self, client):
        for _ in range(6):
            response = await client.post("/api/v1/auth/login", json={
                "username": "testadmin",
                "password": "wrong",
            })
        assert response.status_code == 429
```

### 4.3 API Test Ví dụ - Task Endpoints

```python
# tests/integration/api/test_task_endpoints.py
class TestTaskEndpoints:
    async def test_create_task(self, client, auth_headers):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "module_id": "module-uuid",
                "title": "Implement auth module",
                "description": "Create authentication endpoints",
                "priority": "HIGH",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["state"] == "NEW"
        assert data["retry_count"] == 0

    async def test_create_task_validation_error(self, client, auth_headers):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "module_id": "module-uuid",
                # missing title
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_list_tasks_with_pagination(self, client, auth_headers):
        response = await client.get(
            "/api/v1/tasks?page=1&per_page=10&sort=created_at&order=desc",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert len(data["data"]) <= 10

    async def test_task_transition_valid(self, client, auth_headers, api_key_headers):
        # Create a task first
        create_response = await client.post(
            "/api/v1/tasks",
            json={"module_id": "uuid", "title": "Test", "priority": "MEDIUM"},
            headers=auth_headers,
        )
        task_id = create_response.json()["data"]["id"]

        # Transition NEW → ANALYZING
        response = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "ANALYZING",
                "reason": "Gatekeeper classified",
                "actor": "gatekeeper",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["old_status"] == "NEW"
        assert data["new_status"] == "ANALYZING"

    async def test_task_transition_invalid(self, client, auth_headers, api_key_headers):
        # Create task, transition to DONE
        # ... setup ...

        # Try invalid transition: DONE → IMPLEMENTING
        response = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "IMPLEMENTING",
                "reason": "Invalid",
                "actor": "test",
            },
            headers=api_key_headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "STATE_001"

    async def test_task_retry_escalated(self, client, auth_headers):
        # Create task in ESCALATED state
        # ... setup ...

        response = await client.post(
            f"/api/v1/tasks/{task_id}/retry",
            json={"reason": "Human review complete"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["old_status"] == "ESCALATED"
        assert data["new_status"] == "PLANNING"
        assert data["retry_count"] == 0
```

---

## 5. State Machine Testing

### 5.1 Comprehensive Transition Tests

```python
# tests/integration/state_machine/test_all_transitions.py
import pytest

VALID_TRANSITIONS = [
    ("NEW", "ANALYZING", "gatekeeper"),
    ("NEW", "BLOCKED", "gatekeeper"),
    ("ANALYZING", "PLANNING", "orchestrator"),
    ("ANALYZING", "BLOCKED", "orchestrator"),
    ("ANALYZING", "CANCELLED", "user"),
    ("PLANNING", "IMPLEMENTING", "specialist"),
    ("PLANNING", "BLOCKED", "orchestrator"),
    ("PLANNING", "CANCELLED", "user"),
    ("IMPLEMENTING", "VERIFYING", "specialist"),
    ("IMPLEMENTING", "BLOCKED", "specialist"),
    ("IMPLEMENTING", "FAILED", "system"),
    ("VERIFYING", "REVIEWING", "sandbox"),
    ("VERIFYING", "IMPLEMENTING", "sandbox"),
    ("VERIFYING", "FAILED", "system"),
    ("REVIEWING", "DONE", "auditor"),
    ("REVIEWING", "IMPLEMENTING", "auditor"),
    ("REVIEWING", "ESCALATED", "auditor"),
    ("REVIEWING", "CANCELLED", "user"),
    ("ESCALATED", "PLANNING", "mentor"),
    ("ESCALATED", "FAILED", "mentor"),
    ("BLOCKED", "PLANNING", "orchestrator"),
    ("BLOCKED", "CANCELLED", "user"),
]

TERMINAL_STATES = ["DONE", "FAILED", "CANCELLED"]

INVALID_TRANSITIONS = [
    ("DONE", "IMPLEMENTING"),
    ("DONE", "PLANNING"),
    ("DONE", "ANY"),
    ("FAILED", "IMPLEMENTING"),
    ("FAILED", "PLANNING"),
    ("FAILED", "ANY"),
    ("CANCELLED", "IMPLEMENTING"),
    ("CANCELLED", "ANY"),
    ("VERIFYING", "PLANNING"),
    ("REVIEWING", "PLANNING"),
    ("REVIEWING", "VERIFYING"),
    ("ESCALATED", "IMPLEMENTING"),
    ("ESCALATED", "VERIFYING"),
    ("ESCALATED", "REVIEWING"),
    ("BLOCKED", "IMPLEMENTING"),
    ("BLOCKED", "VERIFYING"),
    ("NEW", "DONE"),
]

class TestAllValidTransitions:
    @pytest.mark.parametrize("from_state,to_state,actor", VALID_TRANSITIONS)
    async def test_valid_transition_succeeds(
        self, db_session, from_state, to_state, actor
    ):
        task = await create_task_in_state(db_session, from_state)
        result = await state_machine.transition(
            task_id=task.id,
            from_state=from_state,
            to_state=to_state,
            reason=f"Test: {from_state} → {to_state}",
            actor=actor,
        )
        assert result.success is True
        assert result.new_state == to_state

        # Verify audit log created
        audit = await get_latest_audit_log(db_session, task.id)
        assert audit is not None
        assert audit.action == "state_transition"
        assert audit.details["from_state"] == from_state
        assert audit.details["to_state"] == to_state

class TestAllInvalidTransitions:
    @pytest.mark.parametrize("from_state,to_state", INVALID_TRANSITIONS)
    async def test_invalid_transition_fails(
        self, db_session, from_state, to_state
    ):
        task = await create_task_in_state(db_session, from_state)
        with pytest.raises(InvalidTransitionError):
            await state_machine.transition(
                task_id=task.id,
                from_state=from_state,
                to_state=to_state,
                reason="Invalid test",
                actor="test",
            )

class TestTerminalStates:
    @pytest.mark.parametrize("terminal_state", TERMINAL_STATES)
    async def test_no_transitions_from_terminal_state(
        self, db_session, terminal_state
    ):
        task = await create_task_in_state(db_session, terminal_state)

        all_states = [
            "NEW", "ANALYZING", "PLANNING", "IMPLEMENTING",
            "VERIFYING", "REVIEWING", "DONE", "ESCALATED",
            "BLOCKED", "FAILED", "CANCELLED",
        ]
        for target in all_states:
            with pytest.raises(InvalidTransitionError):
                await state_machine.transition(
                    task_id=task.id,
                    from_state=terminal_state,
                    to_state=target,
                    reason="Should fail",
                    actor="test",
                )
```

### 5.2 Concurrent Transition Tests

```python
# tests/integration/state_machine/test_concurrent_transitions.py
import pytest
import asyncio

class TestConcurrentTransitions:
    async def test_concurrent_transitions_same_task_race_condition(
        self, db_session
    ):
        """Verify chỉ 1 transition thành công khi có concurrent attempts."""
        task = await create_task_in_state(db_session, "NEW")

        results = await asyncio.gather(
            state_machine.transition(
                task_id=task.id, from_state="NEW", to_state="ANALYZING",
                reason="First attempt", actor="gatekeeper-1",
            ),
            state_machine.transition(
                task_id=task.id, from_state="NEW", to_state="ANALYZING",
                reason="Second attempt", actor="gatekeeper-2",
            ),
            return_exceptions=True,
        )

        successes = [r for r in results if isinstance(r, TransitionResult) and r.success]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 1
        assert len(failures) == 1

    async def test_transition_creates_exactly_one_audit_log(
        self, db_session
    ):
        """Verify audit log integrity dưới concurrent conditions."""
        task = await create_task_in_state(db_session, "NEW")
        await state_machine.transition(
            task_id=task.id, from_state="NEW", to_state="ANALYZING",
            reason="Test", actor="gatekeeper",
        )

        logs = await get_audit_logs(db_session, task.id)
        assert len(logs) == 1
```

---

## 6. Agent Testing (Mock LLM Responses)

### 6.1 LLM Mock Infrastructure

```python
# tests/unit/agents/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_llm_response():
    """Factory fixture cho mock LLM responses."""
    def _make_response(
        content: str = "",
        model: str = "deepseek-v4-flash",
        input_tokens: int = 100,
        output_tokens: int = 50,
        latency_ms: int = 500,
        status: str = "success",
    ):
        return {
            "content": content,
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "latency_ms": latency_ms,
            "status": status,
        }
    return _make_response

@pytest.fixture
def mock_llm_gateway():
    """Mock LLM Gateway cho agent tests."""
    with patch("app.services.llm_gateway.LLMGateway") as mock_class:
        mock_instance = MagicMock()
        mock_instance.call = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance
```

### 6.2 Agent Test Ví dụ - Gatekeeper

```python
# tests/unit/agents/test_gatekeeper.py
class TestGatekeeperAgent:
    async def test_classify_simple_task(self, gatekeeper, mock_llm_gateway):
        mock_llm_gateway.call.return_value = {
            "content": json.dumps({
                "complexity_score": 3,
                "routing": "simple",
                "classification_reason": "Simple CRUD operation",
            }),
            "model": "deepseek-v4-flash",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "latency_ms": 500,
            "status": "success",
        }

        result = await gatekeeper.classify(
            task_title="Create user model",
            task_description="Create a simple User SQLAlchemy model with basic fields",
        )

        assert result.complexity_score == 3
        assert result.routing == "simple"
        assert result.model_assigned == "deepseek-v4-flash"

    async def test_classify_complex_task(self, gatekeeper, mock_llm_gateway):
        mock_llm_gateway.call.return_value = {
            "content": json.dumps({
                "complexity_score": 8,
                "routing": "complex",
                "classification_reason": "Multi-module architecture design",
            }),
            "model": "deepseek-v4-flash",
            "usage": {"input_tokens": 200, "output_tokens": 80},
            "latency_ms": 1200,
            "status": "success",
        }

        result = await gatekeeper.classify(
            task_title="Design authentication system",
            task_description="Design multi-module auth system with OAuth2, JWT, RBAC",
        )

        assert result.complexity_score == 8
        assert result.routing == "complex"
        assert result.model_assigned == "deepseek-v4-pro"

    async def test_classify_with_llm_error_fallback(self, gatekeeper, mock_llm_gateway):
        mock_llm_gateway.call.side_effect = [
            LLMError("Provider unavailable"),  # Primary fails
            {  # Fallback succeeds
                "content": json.dumps({
                    "complexity_score": 5,
                    "routing": "standard",
                    "classification_reason": "Fallback classification",
                }),
                "model": "deepseek-v4-pro",
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "latency_ms": 800,
                "status": "success",
            },
        ]

        result = await gatekeeper.classify(
            task_title="Test task",
            task_description="Test description",
        )

        assert result.complexity_score == 5
        assert result.fallback_used is True
        assert result.fallback_model == "deepseek-v4-pro"
```

### 6.3 Agent Test Ví dụ - Specialist

```python
# tests/unit/agents/test_specialist.py
class TestSpecialistAgent:
    async def test_implement_simple_module(self, specialist, mock_llm_gateway):
        mock_llm_gateway.call.return_value = {
            "content": json.dumps({
                "files": [
                    {
                        "path": "app/models/user.py",
                        "content": "class User(Base):\n    ...",
                    },
                    {
                        "path": "tests/test_user.py",
                        "content": "def test_create_user():\n    ...",
                    },
                ],
                "summary": "Implemented User model with basic CRUD and tests",
            }),
            "model": "deepseek-v4-flash",
            "usage": {"input_tokens": 500, "output_tokens": 1000},
            "latency_ms": 3000,
            "status": "success",
        }

        result = await specialist.implement(
            task_spec="Create User model with name, email, hashed_password fields",
            context={"project_name": "AI SDLC System"},
        )

        assert len(result.files) == 2
        assert result.files[0].path == "app/models/user.py"
        assert result.summary is not None

    async def test_implement_with_context_overflow(self, specialist, mock_llm_gateway):
        """Test specialist xử lý context overflow."""
        mock_llm_gateway.call.side_effect = ContextOverflowError("Token limit exceeded")

        with pytest.raises(ContextOverflowError):
            await specialist.implement(
                task_spec="Very long task description...",
                context={"large_context": "x" * 100000},
            )
```

---

## 7. Workflow Testing (End-to-End)

### 7.1 E2E Test Setup

```python
# tests/e2e/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture(scope="module")
async def e2e_client():
    """E2E test client với real database."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client
```

### 7.2 Full Workflow Test

```python
# tests/e2e/test_full_workflow.py
class TestFullWorkflow:
    @pytest.mark.timeout(120)
    async def test_happy_path_new_to_done(self, e2e_client, auth_headers):
        """
        Test full happy path: NEW → ANALYZING → PLANNING →
        IMPLEMENTING → VERIFYING → REVIEWING → DONE

        Agents được mock trả về predefined responses.
        """
        # Step 1: Create project
        project_response = await e2e_client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "E2E test"},
            headers=auth_headers,
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # Step 2: Create module
        module_response = await e2e_client.post(
            "/api/v1/modules",
            json={
                "project_id": project_id,
                "name": "auth",
                "description": "Authentication module",
            },
            headers=auth_headers,
        )
        assert module_response.status_code == 201
        module_id = module_response.json()["data"]["id"]

        # Step 3: Create task
        task_response = await e2e_client.post(
            "/api/v1/tasks",
            json={
                "module_id": module_id,
                "title": "Implement login endpoint",
                "description": "Create POST /auth/login endpoint",
                "priority": "HIGH",
            },
            headers=auth_headers,
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["data"]["id"]
        assert task_response.json()["data"]["state"] == "NEW"

        # Step 4: Gatekeeper classifies → ANALYZING
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "ANALYZING",
                "reason": "Classified as STANDARD",
                "actor": "gatekeeper",
                "metadata": {"complexity_score": 5, "routing": "standard"},
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200
        assert transition_response.json()["data"]["new_status"] == "ANALYZING"

        # Step 5: Orchestrator plans → PLANNING
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "PLANNING",
                "reason": "Task breakdown complete",
                "actor": "orchestrator",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200
        assert transition_response.json()["data"]["new_status"] == "PLANNING"

        # Step 6: Specialist implements → IMPLEMENTING
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "IMPLEMENTING",
                "reason": "Agent accepted task",
                "actor": "specialist",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # Step 7: Verification pass → VERIFYING
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "VERIFYING",
                "reason": "Code complete, entering sandbox",
                "actor": "specialist",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # Step 8: Sandbox pass → REVIEWING
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "REVIEWING",
                "reason": "Sandbox passed: lint, test, build OK",
                "actor": "sandbox",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # Step 9: Auditor approves → DONE
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "DONE",
                "reason": "Auditor approved, confidence 85%",
                "actor": "auditor",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200
        assert transition_response.json()["data"]["new_status"] == "DONE"

        # Step 10: Verify audit trail
        audit_response = await e2e_client.get(
            f"/api/v1/audit-logs?entity_type=task&entity_id={task_id}",
            headers=auth_headers,
        )
        assert audit_response.status_code == 200
        audits = audit_response.json()["data"]
        assert len(audits) == 6  # 6 transitions

    @pytest.mark.timeout(120)
    async def test_retry_workflow(self, e2e_client, auth_headers):
        """
        Test retry path: IMPLEMENTING → VERIFYING → IMPLEMENTING (retry)
        → VERIFYING → REVIEWING → DONE
        """
        # ... setup project, module, task ...

        # Transition to IMPLEMENTING
        # ... transitions ...

        # VERIFYING → sandbox fail → IMPLEMENTING (retry)
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "IMPLEMENTING",
                "reason": "Sandbox failed: 2 test failures, retrying",
                "actor": "sandbox",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # Second attempt succeeds → VERIFYING → REVIEWING → DONE
        # ... continue transitions ...

    @pytest.mark.timeout(120)
    async def test_escalation_workflow(self, e2e_client, auth_headers):
        """
        Test escalation path: REVIEWING → ESCALATED → PLANNING → ... → DONE
        """
        # ... setup ...

        # REVIEWING → ESCALATED (critical violation)
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "ESCALATED",
                "reason": "Critical law violation detected",
                "actor": "auditor",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # ESCALATED → PLANNING (Mentor takeover)
        transition_response = await e2e_client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={
                "new_status": "PLANNING",
                "reason": "Mentor takeover, new plan created",
                "actor": "mentor",
            },
            headers=auth_headers,
        )
        assert transition_response.status_code == 200

        # Continue through remaining states...
```

---

## 8. Test Infrastructure

### 8.1 Fixtures

```python
# tests/conftest.py
import pytest
from faker import Faker
from app.models import Project, ModuleSpec, Task, User, APIKey

fake = Faker()

@pytest.fixture
def fake_project_data():
    def _make(**overrides):
        return {
            "name": fake.company(),
            "description": fake.text(),
            "tech_stack": ["Python", "FastAPI"],
            **overrides,
        }
    return _make

@pytest.fixture
def fake_task_data():
    def _make(**overrides):
        return {
            "title": fake.sentence(),
            "description": fake.text(),
            "priority": fake.random_element(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            **overrides,
        }
    return _make

@pytest.fixture
def fake_user_data():
    def _make(**overrides):
        return {
            "username": fake.user_name(),
            "email": fake.email(),
            "password": "TestP@ss1!",
            "full_name": fake.name(),
            "role": fake.random_element(["admin", "operator", "developer", "viewer"]),
            **overrides,
        }
    return _make

@pytest.fixture
async def create_test_user(db_session):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)

    async def _create(role="admin", **overrides):
        data = {
            "username": fake.user_name(),
            "email": fake.email(),
            "hashed_password": pwd_context.hash("TestP@ss1!"),
            "full_name": fake.name(),
            "role": role,
        }
        data.update(overrides)
        user = User(**data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create

@pytest.fixture
async def create_test_project(db_session):
    async def _create(**overrides):
        data = {
            "name": fake.company(),
            "description": fake.text(),
            "tech_stack": ["Python", "FastAPI"],
        }
        data.update(overrides)
        project = Project(**data)
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        return project

    return _create

@pytest.fixture
async def auth_token(create_test_user):
    user = await create_test_user(role="admin")
    from app.services.auth import create_access_token
    return create_access_token(user.id)
```

### 8.2 Factories

```python
# tests/factories.py
from factory import Factory, Faker, SubFactory, LazyAttribute
from app.models import Project, ModuleSpec, Task, User

class ProjectFactory(Factory):
    class Meta:
        model = Project

    name = Faker("company")
    description = Faker("text")
    tech_stack = ["Python", "FastAPI"]

class ModuleSpecFactory(Factory):
    class Meta:
        model = ModuleSpec

    project = SubFactory(ProjectFactory)
    name = Faker("word")
    description = Faker("text")
    tech_stack = ["Python"]

class TaskFactory(Factory):
    class Meta:
        model = Task

    module = SubFactory(ModuleSpecFactory)
    title = Faker("sentence")
    description = Faker("text")
    state = "NEW"
    priority = "MEDIUM"
    retry_count = 0
    max_retries = 2

class UserFactory(Factory):
    class Meta:
        model = User

    username = Faker("user_name")
    email = Faker("email")
    hashed_password = "$2b$12$..."  # Pre-hashed
    role = "developer"
    is_active = True
```

### 8.3 Mocks

```python
# tests/mocks/llm_responses.py

MOCK_SPECIALIST_RESPONSE = {
    "files": [
        {"path": "app/auth/login.py", "content": "# Login implementation\n..."},
        {"path": "tests/test_auth.py", "content": "# Auth tests\n..."},
    ],
    "summary": "Implemented login endpoint with JWT authentication",
}

MOCK_AUDITOR_APPROVE_RESPONSE = {
    "verdict": "APPROVED",
    "scores": {
        "spec_match": 0.90,
        "structure": 0.85,
        "architecture": 0.80,
        "clean_code": 0.88,
        "law_compliance": 0.92,
    },
    "violations": [],
    "suggestions": [],
}

MOCK_AUDITOR_REVISE_RESPONSE = {
    "verdict": "REVISE",
    "scores": {
        "spec_match": 0.70,
        "structure": 0.60,
        "architecture": 0.55,
        "clean_code": 0.75,
        "law_compliance": 0.50,
    },
    "violations": [
        {"law": "LAW-002", "description": "Missing input validation"},
    ],
    "suggestions": ["Add Pydantic validation", "Follow LAW-002"],
}

MOCK_AUDITOR_ESCALATE_RESPONSE = {
    "verdict": "ESCALATE",
    "scores": {
        "spec_match": 0.40,
        "structure": 0.30,
        "architecture": 0.25,
        "clean_code": 0.35,
        "law_compliance": 0.20,
    },
    "violations": [
        {"law": "LAW-009", "description": "Critical security vulnerability"},
    ],
    "suggestions": [],
}

MOCK_GATEKEEPER_SIMPLE = {
    "complexity_score": 3,
    "routing": "simple",
    "classification_reason": "Simple CRUD, low complexity",
}

MOCK_GATEKEEPER_COMPLEX = {
    "complexity_score": 8,
    "routing": "complex",
    "classification_reason": "Multi-module design, high complexity",
}

MOCK_ORCHESTRATOR_PLAN = {
    "subtasks": [
        {"title": "Implement login endpoint", "priority": "HIGH", "depends_on": []},
        {"title": "Write login tests", "priority": "HIGH", "depends_on": ["Implement login endpoint"]},
    ],
    "workflow_order": ["Implement login endpoint", "Write login tests"],
}
```

---

## 9. Coverage Target và Measurement

### 9.1 Coverage Configuration

```ini
# .coveragerc
[run]
source = app/
omit =
    app/tests/*
    app/migrations/*
    app/*/migrations/*
    */__pycache__/*
    */site-packages/*

[report]
fail_under = 80
show_missing = True
skip_empty = True
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
    type: ignore
```

### 9.2 Coverage Targets per Module

| Module | Target | Priority |
|--------|--------|----------|
| State Machine Service | 95% | P0 |
| Auth Service | 90% | P0 |
| LLM Gateway | 85% | P0 |
| Task Repository | 90% | P0 |
| API Endpoints | 85% | P1 |
| Cost Calculator | 90% | P1 |
| Circuit Breaker | 90% | P1 |
| Prompt Renderer | 80% | P1 |
| Context Builder | 75% | P2 |
| Agent Services | 70% | P2 |

### 9.3 Coverage Commands

```bash
# Chạy tất cả tests với coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Chạy chỉ unit tests
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Chạy integration tests
pytest tests/integration/ -v --cov=app

# Chạy E2E tests
pytest tests/e2e/ -v --timeout=180

# Chạy với parallel execution
pytest -n auto --cov=app

# Chạy specific module coverage
pytest tests/unit/services/test_state_machine.py --cov=app/services/state_machine --cov-report=term-missing
```

---

## 10. CI Testing Pipeline

### 10.1 GitHub Actions Pipeline

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=app --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: ai_sdlc_test
          POSTGRES_USER: ai_sdlc
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run integration tests
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://ai_sdlc:test_password@localhost:5432/ai_sdlc_test
        run: pytest tests/integration/ -v --timeout=60

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: ai_sdlc_e2e
          POSTGRES_USER: ai_sdlc
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run E2E tests
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://ai_sdlc:test_password@localhost:5432/ai_sdlc_e2e
        run: pytest tests/e2e/ -v --timeout=180

  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run ruff lint
        run: ruff check app/ tests/
      - name: Run mypy typecheck
        run: mypy app/ --ignore-missing-imports
```

### 10.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: detect-private-key
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*