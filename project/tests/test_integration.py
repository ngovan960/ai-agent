import pytest
from httpx import AsyncClient


class TestProjectsIntegration:
    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/projects",
            json={"name": "Integration Test Project", "description": "Test project for integration tests"},
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Integration Test Project"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Get Test Project", "description": "Test"},
        )
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Project"

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient):
        await client.post("/api/v1/projects", json={"name": "Project A", "description": "A"})
        await client.post("/api/v1/projects", json={"name": "Project B", "description": "B"})

        response = await client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Update Test", "description": "Before"},
        )
        project_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated Name", "description": "After"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Delete Test", "description": "To delete"},
        )
        project_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 204

        get_resp = await client.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 404


class TestModulesIntegration:
    @pytest.mark.asyncio
    async def test_create_module(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Module Test Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        response = await client.post(
            "/api/v1/modules",
            json={"name": "Auth Module", "description": "Authentication module", "project_id": project_id},
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Auth Module"

    @pytest.mark.asyncio
    async def test_list_modules(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "List Modules Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        await client.post("/api/v1/modules", json={"name": "Module A", "project_id": project_id})
        await client.post("/api/v1/modules", json={"name": "Module B", "project_id": project_id})

        response = await client.get(f"/api/v1/modules?project_id={project_id}")
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_module(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Get Module Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        create_resp = await client.post(
            "/api/v1/modules",
            json={"name": "Get Test Module", "description": "Test", "project_id": project_id},
        )
        module_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/modules/{module_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Module"


class TestTasksIntegration:
    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Task Test Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Implement Login",
                "description": "User login endpoint",
                "priority": "HIGH",
                "risk_level": "MEDIUM",
                "project_id": project_id,
            },
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["title"] == "Implement Login"
        assert data["status"] == "NEW"

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "List Tasks Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        await client.post("/api/v1/tasks", json={"title": "Task A", "project_id": project_id})
        await client.post("/api/v1/tasks", json={"title": "Task B", "project_id": project_id})

        response = await client.get(f"/api/v1/tasks?project_id={project_id}")
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Get Task Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        create_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Get Test Task", "project_id": project_id},
        )
        task_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get Test Task"


class TestStateTransitionsIntegration:
    @pytest.mark.asyncio
    async def test_valid_transition_new_to_analyzing(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Transition Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Transition Task", "project_id": project_id},
        )
        task_id = task_resp.json()["id"]

        response = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"target_status": "ANALYZING", "reason": "Starting analysis"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json()["status"] == "ANALYZING"

    @pytest.mark.asyncio
    async def test_invalid_transition_new_to_done(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Invalid Transition Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Invalid Transition Task", "project_id": project_id},
        )
        task_id = task_resp.json()["id"]

        response = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"target_status": "DONE", "reason": "Should fail"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_full_workflow_transitions(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Full Workflow Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Full Workflow Task", "project_id": project_id},
        )
        task_id = task_resp.json()["id"]

        transitions = [
            ("ANALYZING", "Analysis complete"),
            ("PLANNING", "Plan created"),
            ("IMPLEMENTING", "Implementation started"),
            ("VERIFYING", "Verification started"),
            ("REVIEWING", "Review started"),
            ("DONE", "Task completed"),
        ]

        for new_status, reason in transitions:
            response = await client.post(
                f"/api/v1/tasks/{task_id}/transition",
                json={"target_status": new_status, "reason": reason},
            )
            assert response.status_code == 200, f"Failed transition to {new_status}: {response.text}"
            assert response.json()["status"] == new_status

    @pytest.mark.asyncio
    async def test_blocked_to_escalated_transition(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Blocked Task Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Blocked Task", "project_id": project_id},
        )
        task_id = task_resp.json()["id"]

        transitions = [
            ("ANALYZING", "Starting analysis"),
            ("BLOCKED", "Blocked on dependency"),
        ]
        for new_status, reason in transitions:
            response = await client.post(
                f"/api/v1/tasks/{task_id}/transition",
                json={"target_status": new_status, "reason": reason},
            )
            assert response.status_code == 200

        response = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"target_status": "ESCALATED", "reason": "Auto-escalated after timeout"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ESCALATED"


class TestValidationGateIntegration:
    @pytest.mark.asyncio
    async def test_validate_task_classification(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/validation/",
            json={
                "user_request": "Implement user login",
                "gatekeeper_classification": {
                    "task_type": "feature_add",
                    "complexity": "medium",
                    "risk_level": "medium",
                    "estimated_effort": "4h",
                    "confidence": 0.85,
                    "reasoning": "Standard feature implementation",
                },
            },
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "verdict" in data

    @pytest.mark.asyncio
    async def test_skip_validation_for_low_risk(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/validation/should-skip?risk_level=low&complexity=trivial"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip_validation"] is True

    @pytest.mark.asyncio
    async def test_no_skip_for_high_risk(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/validation/should-skip?risk_level=high&complexity=complex"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip_validation"] is False

    @pytest.mark.asyncio
    async def test_quick_validate(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/validation/quick",
            params={
                "user_request": "Fix typo in README",
                "task_type": "bug_fix",
                "complexity": "trivial",
                "risk_level": "low",
                "estimated_effort": "10m",
                "confidence": 0.95,
                "reasoning": "Simple documentation fix",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["verdict"] in ["approved", "rejected", "needs_review"]


class TestRetryAuditIntegration:
    @pytest.mark.asyncio
    async def test_create_retry_record(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/retries",
            json={
                "task_id": "00000000-0000-0000-0000-000000000001",
                "reason": "llm_timeout",
                "agent_name": "coder",
                "error_log": "Connection timed out",
            },
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["attempt_number"] == 1
        assert data["reason"] == "llm_timeout"

    @pytest.mark.asyncio
    async def test_get_retry_stats(self, client: AsyncClient):
        task_id = "00000000-0000-0000-0000-000000000002"

        await client.post(
            "/api/v1/retries",
            json={"task_id": task_id, "reason": "llm_error", "agent_name": "coder"},
        )
        await client.post(
            "/api/v1/retries",
            json={"task_id": task_id, "reason": "llm_timeout", "agent_name": "coder"},
        )

        response = await client.get(f"/api/v1/tasks/{task_id}/retries/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_retries"] == 2

    @pytest.mark.asyncio
    async def test_can_retry_true(self, client: AsyncClient):
        task_id = "00000000-0000-0000-0000-000000000003"

        response = await client.get(f"/api/v1/tasks/{task_id}/retries/can-retry")
        assert response.status_code == 200
        assert response.json()["can_retry"] is True

    @pytest.mark.asyncio
    async def test_create_audit_log(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/audit-logs",
            json={
                "action": "state_transition",
                "actor": "orchestrator",
                "result": "SUCCESS",
                "message": "Task moved from NEW to ANALYZING",
            },
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["action"] == "state_transition"

    @pytest.mark.asyncio
    async def test_query_audit_logs(self, client: AsyncClient):
        await client.post(
            "/api/v1/audit-logs",
            json={"action": "create_task", "actor": "user", "result": "SUCCESS"},
        )
        await client.post(
            "/api/v1/audit-logs",
            json={"action": "transition", "actor": "orchestrator", "result": "SUCCESS"},
        )

        response = await client.get("/api/v1/audit-logs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert "logs" in data

    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, client: AsyncClient):
        await client.post(
            "/api/v1/audit-logs",
            json={"action": "test_action", "actor": "test_actor", "result": "SUCCESS"},
        )

        response = await client.get("/api/v1/audit-logs/export/csv")
        assert response.status_code == 200
        data = response.json()
        assert "csv" in data
        assert "id,task_id,action,actor,actor_type,result,message,created_at" in data["csv"]

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client: AsyncClient):
        task_id = "00000000-0000-0000-0000-000000000004"

        for i in range(5):
            response = await client.post(
                "/api/v1/retries",
                json={"task_id": task_id, "reason": "llm_error", "agent_name": "coder"},
            )
            assert response.status_code == 200

        response = await client.post(
            "/api/v1/retries",
            json={"task_id": task_id, "reason": "llm_error", "agent_name": "coder"},
        )
        assert response.status_code == 400

        can_retry_resp = await client.get(f"/api/v1/tasks/{task_id}/retries/can-retry")
        assert can_retry_resp.json()["can_retry"] is False


class TestEndToEndWorkflow:
    @pytest.mark.asyncio
    async def test_full_project_module_task_workflow(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "E2E Project", "description": "End-to-end test"},
        )
        assert project_resp.status_code == 201
        project_id = project_resp.json()["id"]

        module_resp = await client.post(
            "/api/v1/modules",
            json={"name": "E2E Module", "description": "Module for E2E test", "project_id": project_id},
        )
        assert module_resp.status_code == 201
        module_id = module_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "E2E Task", "description": "Task for E2E test", "priority": "HIGH", "project_id": project_id},
        )
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]

        validation_resp = await client.post(
            "/api/v1/validation/",
            json={
                "user_request": "E2E task request",
                "gatekeeper_classification": {
                    "task_type": "feature_add",
                    "complexity": "medium",
                    "risk_level": "medium",
                    "estimated_effort": "2h",
                    "confidence": 0.9,
                    "reasoning": "E2E test task",
                },
            },
        )
        assert validation_resp.status_code == 201

        transition_resp = await client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"target_status": "ANALYZING", "reason": "Validation passed"},
        )
        assert transition_resp.status_code == 200
        assert transition_resp.json()["status"] == "ANALYZING"

        audit_resp = await client.post(
            "/api/v1/audit-logs",
            json={
                "action": "e2e_workflow",
                "actor": "test_runner",
                "result": "SUCCESS",
                "message": "Full E2E workflow completed",
            },
        )
        assert audit_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_task_retry_and_audit_flow(self, client: AsyncClient):
        project_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Retry Flow Project", "description": "Test"},
        )
        project_id = project_resp.json()["id"]

        task_resp = await client.post(
            "/api/v1/tasks",
            json={"title": "Retry Flow Task", "project_id": project_id},
        )
        task_id = task_resp.json()["id"]

        retry_resp = await client.post(
            "/api/v1/retries",
            json={
                "task_id": task_id,
                "reason": "llm_timeout",
                "agent_name": "coder",
                "error_log": "Timeout after 30s",
            },
        )
        assert retry_resp.status_code == 200
        assert retry_resp.json()["attempt_number"] == 1

        audit_resp = await client.post(
            "/api/v1/audit-logs",
            json={
                "action": "retry_attempted",
                "actor": "orchestrator",
                "result": "FAILURE",
                "message": "Task retry due to LLM timeout",
            },
        )
        assert audit_resp.status_code == 200

        stats_resp = await client.get(f"/api/v1/tasks/{task_id}/retries/stats")
        assert stats_resp.json()["total_retries"] == 1

        logs_resp = await client.get(f"/api/v1/tasks/{task_id}/audit-logs")
        assert logs_resp.status_code == 200


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
