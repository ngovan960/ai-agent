# REST API Specification - AI SDLC System

## Tài liệu Đặc tả API REST

---

## 1. REST API Design Principles

### 1.1 Nguyên tắc Thiết kế

| # | Nguyên tắc | Mô tả |
|---|-----------|--------|
| 1 | **Resource-oriented** | URL biểu diễn resource (danh từ), không phải action (động từ) |
| 2 | **Stateless** | Mỗi request chứa mọi thông tin cần thiết, server không lưu session state |
| 3 | **Consistent naming** | URL sử dụng snake_case, plural nouns cho collections |
| 4 | **HTTP methods** | Dùng đúng semantics: GET (đọc), POST (tạo), PUT (cập nhật toàn bộ), PATCH (cập nhật một phần), DELETE (xoá) |
| 5 | **HATEOAS-lite** | Response bao gồm related links cho navigation |
| 6 | **Idempotency** | PUT và DELETE phải idempotent; POST không bắt buộc |
| 7 | **Pagination** | Mọi collection endpoint phải hỗ trợ pagination |
| 8 | **Filtering & Sorting** | Hỗ trợ query parameters cho filter/sort |
| 9 | **Versioning** | API version trong URL prefix: `/api/v1/` |

### 1.2 URL Conventions

```
Base URL: https://api.ai-sdlc.example.com/api/v1

Resource URLs:
  GET    /api/v1/projects              → List projects
  POST   /api/v1/projects              → Create project
  GET    /api/v1/projects/{id}         → Get project detail
  PUT    /api/v1/projects/{id}         → Update project (full)
  PATCH  /api/v1/projects/{id}         → Update project (partial)
  DELETE /api/v1/projects/{id}         → Delete project

Nested Resources:
  GET    /api/v1/projects/{id}/modules → List modules in project
  GET    /api/v1/projects/{id}/tasks    → List tasks in project

Actions (verbs on resources):
  POST   /api/v1/tasks/{id}/transition → Transition task state
  POST   /api/v1/tasks/{id}/retry      → Retry escalated task
```

---

## 2. API Versioning

### 2.1 URL-based Versioning

```
/api/v1/    ← Current stable version
/api/v2/    ← Future version (khi có breaking changes)
```

**Quy tắc:**
- Major version trong URL prefix
- Minor version và patch không thay đổi API contract
- V1 được hỗ trợ ít nhất 6 tháng sau khi V2 release
- Breaking changes: xoá field, đổi type, thay đổi semantics

### 2.2 Version Headers

```http
GET /api/v1/projects HTTP/1.1
Accept: application/json
X-API-Version: 1.0
```

Response header luôn bao gồm:

```http
HTTP/1.1 200 OK
X-API-Version: 1.0
Content-Type: application/json
```

---

## 3. Authentication

### 3.1 JWT Bearer Authentication

**Login:**

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "ngovan960",
  "password": "SecureP@ss1!"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid-here",
    "username": "ngovan960",
    "role": "admin"
  }
}
```

**Sử dụng Access Token:**

```http
GET /api/v1/projects HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Refresh Token:**

```http
POST /api/v1/auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 3.2 API Key Authentication

Cho agent-to-agent communication:

```http
POST /api/v1/tasks/123e4567-e89b-12d3/transition HTTP/1.1
X-API-Key: aislk_live_abc123def456ghi789jkl012mno345pqr678
Content-Type: application/json

{
  "new_status": "ANALYZING",
  "reason": "Gatekeeper classified task",
  "actor": "gatekeeper-agent"
}
```

### 3.3 Auth Error Responses

```json
// 401 Unauthorized - Missing or invalid token
{
  "error": {
    "code": "AUTH_001",
    "message": "Authentication required",
    "details": "Missing Authorization header"
  }
}

// 401 Unauthorized - Expired token
{
  "error": {
    "code": "AUTH_002",
    "message": "Token expired",
    "details": "Access token has expired. Please refresh."
  }
}

// 403 Forbidden - Insufficient permissions
{
  "error": {
    "code": "AUTH_003",
    "message": "Insufficient permissions",
    "details": "Role 'viewer' cannot create projects"
  }
}
```

---

## 4. Common Response Format

### 4.1 Success Response

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_uuid_here",
    "timestamp": "2026-05-14T10:00:00Z",
    "version": "1.0"
  }
}
```

### 4.2 Single Resource Response

```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "AI SDLC System",
    "description": "Main project",
    "created_at": "2026-05-14T10:00:00Z",
    "updated_at": "2026-05-14T10:00:00Z"
  },
  "meta": {
    "request_id": "req_uuid_here",
    "timestamp": "2026-05-14T10:00:00Z",
    "version": "1.0"
  }
}
```

### 4.3 Collection Response with Pagination

```json
{
  "data": [
    { "id": "...", "name": "..." },
    { "id": "...", "name": "..." }
  ],
  "meta": {
    "request_id": "req_uuid_here",
    "timestamp": "2026-05-14T10:00:00Z",
    "version": "1.0"
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 157,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 5. Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_001",
    "message": "Validation error",
    "details": [
      {
        "field": "title",
        "message": "Title is required"
      },
      {
        "field": "priority",
        "message": "Must be one of: LOW, MEDIUM, HIGH, CRITICAL"
      }
    ]
  },
  "meta": {
    "request_id": "req_uuid_here",
    "timestamp": "2026-05-14T10:00:00Z",
    "version": "1.0"
  }
}
```

### 5.1 Error Code Hierarchy

| Category | Prefix | Range | Ví dụ |
|----------|--------|-------|-------|
| Authentication | `AUTH_` | 001-099 | AUTH_001: Missing token |
| Authorization | `AUTH_` | 100-199 | AUTH_100: Insufficient role |
| Validation | `VALIDATION_` | 001-099 | VALIDATION_001: Field required |
| State Machine | `STATE_` | 001-099 | STATE_001: Invalid transition |
| Resource | `RESOURCE_` | 001-099 | RESOURCE_001: Not found |
| Rate Limit | `RATE_` | 001-099 | RATE_001: Too many requests |
| Internal | `INTERNAL_` | 001-099 | INTERNAL_001: Database error |

### 5.2 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | GET, PUT, PATCH success |
| 201 | Created | POST success |
| 204 | No Content | DELETE success |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource, invalid state |
| 422 | Unprocessable Entity | Business logic violation |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected error |
| 503 | Service Unavailable | Database/LLM unavailable |

---

## 6. Pagination Format

### 6.1 Query Parameters

```
GET /api/v1/tasks?page=2&per_page=20&sort=created_at&order=desc
```

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|--------|
| `page` | integer | 1 | Trang hiện tại (1-indexed) |
| `per_page` | integer | 20 | Số items per page (max: 100) |
| `sort` | string | `created_at` | Field để sort |
| `order` | string | `desc` | `asc` hoặc `desc` |

### 6.2 Filtering

```
GET /api/v1/tasks?state=IMPLEMENTING&priority=HIGH&project_id=uuid
```

### 6.3 Pagination Response

```json
{
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total_items": 157,
    "total_pages": 8,
    "has_next": true,
    "has_prev": true,
    "next_page": "/api/v1/tasks?page=3&per_page=20",
    "prev_page": "/api/v1/tasks?page=1&per_page=20"
  }
}
```

---

## 7. API Endpoints

### 7.1 Auth Endpoints

#### POST /api/v1/auth/login

Đăng nhập và nhận JWT tokens.

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "ngovan960",
  "password": "SecureP@ss1!"
}
```

**Response 200:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "123e4567-e89b-12d3",
      "username": "ngovan960",
      "email": "n***@example.com",
      "role": "admin",
      "full_name": "Ngovan 960"
    }
  },
  "meta": {
    "request_id": "req_uuid",
    "timestamp": "2026-05-14T10:00:00Z",
    "version": "1.0"
  }
}
```

**Error Responses:**

| Status | Code | Condition |
|--------|------|-----------|
| 401 | AUTH_001 | Invalid username/password |
| 429 | RATE_001 | Too many login attempts (>5/min) |

#### POST /api/v1/auth/refresh

Refresh access token.

```http
POST /api/v1/auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

**Response 200:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiJ9...(new)",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

#### POST /api/v1/auth/logout

Logout và revoke refresh token.

```http
POST /api/v1/auth/logout HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

**Response 204:** No Content

#### POST /api/v1/api-keys

Tạo API key mới.

```http
POST /api/v1/api-keys HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "gatekeeper-agent-key",
  "permissions": ["read:tasks", "write:task_status", "read:memory"],
  "expires_at": "2027-05-14T00:00:00Z"
}
```

**Response 201:**

```json
{
  "data": {
    "id": "uuid-here",
    "name": "gatekeeper-agent-key",
    "key": "aislk_live_abc123def456ghi789jkl012mno345pqr678",
    "key_prefix": "aislk_li",
    "permissions": ["read:tasks", "write:task_status", "read:memory"],
    "expires_at": "2027-05-14T00:00:00Z",
    "created_at": "2026-05-14T10:00:00Z"
  },
  "meta": { ... }
}
```

> **Lưu ý**: `key` chỉ hiển thị 1 lần khi tạo. Sau đó chỉ có `key_prefix`.

---

### 7.2 Projects Endpoints

#### GET /api/v1/projects

List tất cả projects user có quyền truy cập.

```http
GET /api/v1/projects?page=1&per_page=20&sort=created_at&order=desc HTTP/1.1
Authorization: Bearer <access_token>
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "123e4567-e89b-12d3",
      "name": "AI SDLC System",
      "description": "Main project for AI-powered SDLC",
      "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
      "status": "active",
      "created_at": "2026-05-14T10:00:00Z",
      "updated_at": "2026-05-14T10:00:00Z"
    }
  ],
  "pagination": { ... },
  "meta": { ... }
}
```

#### POST /api/v1/projects

Tạo project mới. Yêu cầu role: `developer` trở lên.

```http
POST /api/v1/projects HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "AI SDLC System",
  "description": "AI-powered SDLC automation platform",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis"]
}
```

**Response 201:**

```json
{
  "data": {
    "id": "123e4567-e89b-12d3",
    "name": "AI SDLC System",
    "description": "AI-powered SDLC automation platform",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis"],
    "status": "active",
    "created_at": "2026-05-14T10:00:00Z",
    "updated_at": "2026-05-14T10:00:00Z"
  }
}
```

#### GET /api/v1/projects/{id}

Lấy chi tiết project.

**Response 200:** Same structure as POST response, thêm:

```json
{
  "data": {
    "id": "123e4567-e89b-12d3",
    "name": "AI SDLC System",
    "description": "...",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    "status": "active",
    "stats": {
      "total_modules": 12,
      "total_tasks": 45,
      "completed_tasks": 30,
      "active_tasks": 10,
      "failed_tasks": 5
    },
    "created_at": "2026-05-14T10:00:00Z",
    "updated_at": "2026-05-14T10:00:00Z"
  }
}
```

#### PUT /api/v1/projects/{id}

Cập nhật toàn bộ project.

#### PATCH /api/v1/projects/{id}

Cập nhật một phần project.

```http
PATCH /api/v1/projects/123e4567-e89b-12d3 HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "description": "Updated description"
}
```

#### DELETE /api/v1/projects/{id}

Xoá project (soft delete). Yêu cầu role: `operator` trở lên.

**Response 204:** No Content

---

### 7.3 Modules Endpoints

#### GET /api/v1/modules

List modules, hỗ trợ filter theo project.

```
GET /api/v1/modules?project_id=uuid&page=1&per_page=20
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "uuid",
      "project_id": "123e4567-e89b-12d3",
      "name": "auth",
      "description": "Authentication module",
      "tech_stack": ["Python", "FastAPI"],
      "status": "active",
      "created_at": "2026-05-14T10:00:00Z",
      "updated_at": "2026-05-14T10:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

#### POST /api/v1/modules

```http
POST /api/v1/modules HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "project_id": "123e4567-e89b-12d3",
  "name": "auth",
  "description": "User authentication and authorization",
  "tech_stack": ["Python", "FastAPI", "bcrypt"]
}
```

**Response 201:**

```json
{
  "data": {
    "id": "uuid-here",
    "project_id": "123e4567-e89b-12d3",
    "name": "auth",
    "description": "User authentication and authorization",
    "tech_stack": ["Python", "FastAPI", "bcrypt"],
    "status": "active",
    "created_at": "2026-05-14T10:00:00Z",
    "updated_at": "2026-05-14T10:00:00Z"
  }
}
```

#### GET /api/v1/modules/{id}

#### PUT /api/v1/modules/{id}

#### PATCH /api/v1/modules/{id}

#### DELETE /api/v1/modules/{id}

---

### 7.4 Tasks Endpoints

#### GET /api/v1/tasks

List tasks với filtering rộng.

```
GET /api/v1/tasks?
  project_id=uuid&
  module_id=uuid&
  state=IMPLEMENTING&
  priority=HIGH&
  assigned_agent=specialist&
  page=1&
  per_page=20&
  sort=created_at&
  order=desc
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "task-uuid",
      "module_id": "module-uuid",
      "title": "Implement user authentication",
      "description": "Create login/register/logout endpoints",
      "state": "IMPLEMENTING",
      "priority": "HIGH",
      "complexity_score": 7,
      "assigned_agent": "specialist",
      "retry_count": 0,
      "max_retries": 2,
      "depends_on": ["task-uuid-1"],
      "created_at": "2026-05-14T10:00:00Z",
      "updated_at": "2026-05-14T10:30:00Z",
      "state_history": [
        {
          "from_state": "NEW",
          "to_state": "ANALYZING",
          "actor": "gatekeeper",
          "reason": "Classified as STANDARD complexity",
          "timestamp": "2026-05-14T10:00:05Z"
        },
        {
          "from_state": "ANALYZING",
          "to_state": "PLANNING",
          "actor": "orchestrator",
          "reason": "Task breakdown complete",
          "timestamp": "2026-05-14T10:05:00Z"
        },
        {
          "from_state": "PLANNING",
          "to_state": "IMPLEMENTING",
          "actor": "specialist",
          "reason": "Agent accepted task",
          "timestamp": "2026-05-14T10:10:00Z"
        }
      ]
    }
  ],
  "pagination": { ... }
}
```

#### POST /api/v1/tasks

Tạo task mới. Task luôn bắt đầu ở state `NEW`.

```http
POST /api/v1/tasks HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "module_id": "module-uuid",
  "title": "Implement user authentication",
  "description": "Create login/register/logout endpoints with JWT authentication",
  "priority": "HIGH",
  "depends_on": []
}
```

**Response 201:**

```json
{
  "data": {
    "id": "task-uuid",
    "module_id": "module-uuid",
    "title": "Implement user authentication",
    "description": "Create login/register/logout endpoints with JWT authentication",
    "state": "NEW",
    "priority": "HIGH",
    "complexity_score": null,
    "assigned_agent": null,
    "retry_count": 0,
    "max_retries": 2,
    "depends_on": [],
    "created_at": "2026-05-14T10:00:00Z",
    "updated_at": "2026-05-14T10:00:00Z"
  }
}
```

#### GET /api/v1/tasks/{id}

Lấy chi tiết task, bao gồm state history và retry records.

#### PATCH /api/v1/tasks/{id}

Cập nhật task (chỉ được sửa `title`, `description`, `priority`).

#### DELETE /api/v1/tasks/{id}

Soft delete task. Chỉ được xoá task ở state `NEW`.

#### POST /api/v1/tasks/{id}/transition

Thực hiện state transition. Đây là endpoint quan trọng nhất của state machine.

```http
POST /api/v1/tasks/task-uuid/transition HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "new_status": "ANALYZING",
  "reason": "Gatekeeper classified task as STANDARD complexity, score 7",
  "actor": "gatekeeper-agent",
  "metadata": {
    "complexity_score": 7,
    "routing_decision": "standard"
  }
}
```

**Response 200:**

```json
{
  "data": {
    "task_id": "task-uuid",
    "old_status": "NEW",
    "new_status": "ANALYZING",
    "reason": "Gatekeeper classified task as STANDARD complexity, score 7",
    "actor": "gatekeeper-agent",
    "transition_id": "transition-uuid",
    "timestamp": "2026-05-14T10:00:05Z"
  }
}
```

**Error Responses:**

```json
// Invalid transition
{
  "error": {
    "code": "STATE_001",
    "message": "Invalid state transition",
    "details": "Cannot transition from DONE to IMPLEMENTING. Task has already completed."
  }
}

// Terminal state
{
  "error": {
    "code": "STATE_002",
    "message": "Cannot transition from terminal state",
    "details": "Task is in FAILED state which is terminal. No transitions allowed."
  }
}

// Missing dependency
{
  "error": {
    "code": "STATE_003",
    "message": "Dependency not satisfied",
    "details": "Task depends on task-uuid-1 which is still in PLANNING state."
  }
}
```

#### POST /api/v1/tasks/{id}/retry

Retry escalated task. Reset retry count về 0, chuyển về `PLANNING`.

```http
POST /api/v1/tasks/task-uuid/retry HTTP/1.1
Authorization: Bearer <access_token>

{
  "reason": "Human review complete, retrying with updated context"
}
```

**Response 200:**

```json
{
  "data": {
    "task_id": "task-uuid",
    "old_status": "ESCALATED",
    "new_status": "PLANNING",
    "retry_count": 0,
    "max_retries": 2,
    "reason": "Human review complete, retrying with updated context"
  }
}
```

---

### 7.5 Workflows Endpoints

#### GET /api/v1/workflows

List active workflows.

```http
GET /api/v1/workflows?project_id=uuid&status=active HTTP/1.1
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "workflow-uuid",
      "project_id": "project-uuid",
      "task_id": "task-uuid",
      "current_state": "IMPLEMENTING",
      "started_at": "2026-05-14T10:00:00Z",
      "updated_at": "2026-05-14T10:10:00Z",
      "agent_assignments": [
        {
          "state": "ANALYZING",
          "agent": "gatekeeper",
          "assigned_at": "2026-05-14T10:00:05Z",
          "completed_at": "2026-05-14T10:05:00Z"
        },
        {
          "state": "PLANNING",
          "agent": "orchestrator",
          "assigned_at": "2026-05-14T10:05:00Z",
          "completed_at": "2026-05-14T10:10:00Z"
        },
        {
          "state": "IMPLEMENTING",
          "agent": "specialist",
          "assigned_at": "2026-05-14T10:10:00Z",
          "completed_at": null
        }
      ]
    }
  ],
  "pagination": { ... }
}
```

#### GET /api/v1/workflows/{id}

Chi tiết workflow, bao gồm full history.

#### POST /api/v1/workflows/{id}/cancel

Cancel active workflow. Task chuyển sang `CANCELLED`.

```http
POST /api/v1/workflows/workflow-uuid/cancel HTTP/1.1
Authorization: Bearer <access_token>

{
  "reason": "Business requirements changed"
}
```

---

### 7.6 Audit Logs Endpoints

#### GET /api/v1/audit-logs

List audit logs với filtering.

```
GET /api/v1/audit-logs?
  entity_type=task&
  entity_id=uuid&
  action=state_transition&
  actor=gatekeeper&
  from_date=2026-05-01&
  to_date=2026-05-14&
  page=1&
  per_page=50
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "audit-uuid",
      "entity_type": "task",
      "entity_id": "task-uuid",
      "action": "state_transition",
      "actor": "gatekeeper-agent",
      "actor_type": "agent",
      "details": {
        "from_state": "NEW",
        "to_state": "ANALYZING",
        "reason": "Classified as STANDARD"
      },
      "entry_hash": "sha256hash...",
      "prev_hash": "sha256prevhash...",
      "created_at": "2026-05-14T10:00:05Z"
    }
  ],
  "pagination": { ... }
}
```

#### GET /api/v1/audit-logs/verify

Verify audit log integrity (hash chain validation).

```http
GET /api/v1/audit-logs/verify?entity_type=task&entity_id=uuid HTTP/1.1
```

**Response 200:**

```json
{
  "data": {
    "verified": true,
    "total_entries": 45,
    "verified_entries": 45,
    "tampered_entries": 0,
    "checked_at": "2026-05-14T12:00:00Z"
  }
}
```

---

### 7.7 Cost Tracking Endpoints

#### GET /api/v1/cost-stats

Lấy thống kê chi phí. Yêu cầu role: `operator` trở lên.

```
GET /api/v1/cost-stats?
  project_id=uuid&
  date_from=2026-05-01&
  date_to=2026-05-14&
  group_by=model&
  page=1&
  per_page=50
```

**Response 200:**

```json
{
  "data": {
    "summary": {
      "total_cost_usd": 127.45,
      "total_calls": 1523,
      "total_input_tokens": 2450000,
      "total_output_tokens": 890000,
      "avg_latency_ms": 2340,
      "total_errors": 12,
      "total_fallbacks": 5,
      "period": {
        "from": "2026-05-01",
        "to": "2026-05-14"
      }
    },
    "breakdown_by_model": [
      {
        "model": "deepseek-v4-flash",
        "total_cost_usd": 15.30,
        "total_calls": 800,
        "total_input_tokens": 1200000,
        "total_output_tokens": 400000,
        "avg_latency_ms": 850,
        "error_count": 3,
        "fallback_count": 1
      },
      {
        "model": "deepseek-v4-pro",
        "total_cost_usd": 45.20,
        "total_calls": 350,
        "total_input_tokens": 800000,
        "total_output_tokens": 300000,
        "avg_latency_ms": 3200,
        "error_count": 5,
        "fallback_count": 2
      },
      {
        "model": "qwen-3.5-plus",
        "total_cost_usd": 28.50,
        "total_calls": 250,
        "total_input_tokens": 300000,
        "total_output_tokens": 120000,
        "avg_latency_ms": 2800,
        "error_count": 3,
        "fallback_count": 1
      },
      {
        "model": "qwen-3.6-plus",
        "total_cost_usd": 38.45,
        "total_calls": 123,
        "total_input_tokens": 150000,
        "total_output_tokens": 70000,
        "avg_latency_ms": 4500,
        "error_count": 1,
        "fallback_count": 1
      }
    ],
    "breakdown_by_agent": [
      {
        "agent_type": "specialist",
        "total_cost_usd": 52.10,
        "total_calls": 500
      },
      {
        "agent_type": "orchestrator",
        "total_cost_usd": 28.30,
        "total_calls": 200
      }
    ],
    "daily_trend": [
      {
        "date": "2026-05-01",
        "total_cost_usd": 8.50,
        "total_calls": 95
      },
      {
        "date": "2026-05-02",
        "total_cost_usd": 9.20,
        "total_calls": 110
      }
    ]
  }
}
```

#### GET /api/v1/cost-stats/project/{project_id}

Chi phí theo project cụ thể.

#### GET /api/v1/cost-stats/alerts

Lấy cost alerts cho project.

```http
GET /api/v1/cost-stats/alerts?project_id=uuid HTTP/1.1
```

**Response 200:**

```json
{
  "data": [
    {
      "id": "alert-uuid",
      "project_id": "project-uuid",
      "level": "WARNING",
      "message": "Daily cost $6.50 exceeds warning threshold $5.00",
      "threshold_usd": 5.00,
      "actual_usd": 6.50,
      "created_at": "2026-05-14T15:00:00Z"
    }
  ]
}
```

---

### 7.8 Health Endpoint

#### GET /health

Health check endpoint, không yêu cầu authentication.

```http
GET /health HTTP/1.1
```

**Response 200:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5,
      "schema_version": "013_add_hash_chain_audit"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1
    },
    "llm_providers": {
      "deepseek": {
        "status": "healthy",
        "circuit_breaker": "closed",
        "last_check": "2026-05-14T12:00:00Z"
      },
      "qwen": {
        "status": "healthy",
        "circuit_breaker": "closed",
        "last_check": "2026-05-14T12:00:00Z"
      }
    }
  }
}
```

**Degraded Response:**

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "redis": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "llm_providers": {
      "deepseek": {
        "status": "healthy",
        "circuit_breaker": "closed"
      },
      "qwen": {
        "status": "unhealthy",
        "circuit_breaker": "open",
        "last_error": "503 Service Unavailable"
      }
    }
  }
}
```

---

## 8. Rate Limiting

### 8.1 Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 187
X-RateLimit-Reset: 1716198000
```

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1716198000
Retry-After: 30
```

### 8.2 Rate Limit Configuration

Tham chiếu chi tiết tại `security-design.md` Section 3.1.

---

## 9. Request/Response Schemas

### 9.1 Common Field Types

| Field | Type | Format | Ví dụ |
|-------|------|--------|--------|
| `id` | UUID | UUID v4 | `123e4567-e89b-12d3-a456-426614174000` |
| `created_at` | Timestamp | ISO 8601 | `2026-05-14T10:00:00Z` |
| `state` | Enum | UPPERCASE | `ANALYZING`, `IMPLEMENTING` |
| `priority` | Enum | UPPERCASE | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `cost_usd` | Decimal | 6 decimal places | `0.004530` |
| `latency_ms` | Integer | milliseconds | `2340` |

### 9.2 Task State Enum Values

```
NEW | ANALYZING | PLANNING | IMPLEMENTING | VERIFYING | REVIEWING |
DONE | ESCALATED | BLOCKED | FAILED | CANCELLED
```

### 9.3 Priority Enum Values

```
LOW | MEDIUM | HIGH | CRITICAL
```

### 9.4 Agent Type Enum Values

```
gatekeeper | orchestrator | specialist | auditor | mentor | devops | monitoring
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*