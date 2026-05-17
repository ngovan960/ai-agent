# API Specification

## AI SDLC Orchestrator — REST API Endpoints

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/projects` | List all projects |
| `POST` | `/api/v1/projects` | Create a new project |
| `GET` | `/api/v1/projects/{id}` | Get project by ID |
| `PATCH` | `/api/v1/projects/{id}` | Update project |
| `DELETE` | `/api/v1/projects/{id}` | Delete project |

---

## Modules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/modules` | Create a new module |
| `GET` | `/api/v1/modules` | List all modules |
| `GET` | `/api/v1/modules/{id}` | Get module by ID |
| `PATCH` | `/api/v1/modules/{id}` | Update module |
| `DELETE` | `/api/v1/modules/{id}` | Delete module |
| `POST` | `/api/v1/modules/{id}/dependencies` | Add module dependency |

---

## Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tasks` | Create a new task |
| `GET` | `/api/v1/tasks` | List all tasks |
| `GET` | `/api/v1/tasks/{id}` | Get task by ID |
| `PATCH` | `/api/v1/tasks/{id}` | Update task |
| `DELETE` | `/api/v1/tasks/{id}` | Delete task |
| `POST` | `/api/v1/tasks/{id}/dependencies` | Add task dependency |
| `POST` | `/api/v1/tasks/{id}/transition` | Transition task state |
| `POST` | `/api/v1/tasks/{id}/execute` | Execute task |

---

## Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/summary` | Get dashboard summary (projects, tasks, cost, etc.) |
| `GET` | `/api/v1/dashboard/tasks-by-status` | Get task counts grouped by status |
| `GET` | `/api/v1/dashboard/cost-breakdown` | Get cost breakdown by model |
| `GET` | `/api/v1/dashboard/recent-activity?limit=10` | Get recent audit log entries |
| `WS` | `/api/v1/ws` | WebSocket for real-time updates |

---

## Audit Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/audit-logs?page=1&limit=20` | List audit logs (paginated) |
| `GET` | `/api/v1/audit-logs/export` | Export all audit logs as CSV |

---

## Governance

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/governance/laws` | List all 20 architectural laws |
| `GET` | `/api/v1/governance/violations` | List law violations |
| `POST` | `/api/v1/governance/scan` | Run compliance scan on code |
| `GET` | `/api/v1/governance/report` | Get compliance report |

---

## Model Selection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/models/select` | Select model based on task profile |
| `GET` | `/api/v1/models/capabilities` | Get model capability scores |
| `GET` | `/api/v1/models/cost-stats` | Get model cost statistics |

---

## Verification

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/verify` | Run verification pipeline (dev/prod mode) |
| `GET` | `/api/v1/verify/{task_id}` | Get verification result (cached) |
| `POST` | `/api/v1/verify/{task_id}/rollback` | Trigger rollback for failed task |

---

## WebSocket

```
ws://localhost:8000/api/v1/ws
```

Real-time updates for:
- Task state changes
- New audit log entries
- Agent activity
- Cost updates

---

## Authentication

All endpoints require one of:
- **JWT Bearer Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <key>`

### Auth Endpoints (Planned)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | Login with username/password |
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/api-keys` | Create new API key |

---

## Error Responses

All endpoints return standard error format:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (optimistic lock) |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Interactive Docs

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
**Total Endpoints**: 30+
