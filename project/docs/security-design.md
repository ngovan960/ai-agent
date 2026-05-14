# Security Design - AI SDLC System

## Overview
Tài liệu này mô tả thiết kế bảo mật toàn diện cho AI SDLC System, bao gồm Authentication, Authorization, API Security, Secret Management, Data Security, Agent Security, OpenCode Security và Threat Model.

---

## 1. Authentication Design

### 1.1 JWT-Based Authentication cho API

Hệ thống sử dụng JSON Web Tokens (JWT) để authenticate người dùng qua API REST.

**Flow:**
```
Client → POST /api/v1/auth/login (username + password)
       ← JWT Access Token (15 phút) + Refresh Token (7 ngày)

Client → GET /api/v1/tasks (Authorization: Bearer <access_token>)
       ← 200 OK

Client → POST /api/v1/auth/refresh (refresh_token)
       ← New JWT Access Token + New Refresh Token
```

**JWT Payload:**
```json
{
  "sub": "user_id_uuid",
  "username": "ngovan960",
  "role": "admin",
  "exp": 1716198000,
  "iat": 1716197100,
  "type": "access"
}
```

**Refresh Token Payload:**
```json
{
  "sub": "user_id_uuid",
  "type": "refresh",
  "exp": 1716797100,
  "iat": 1716197100,
  "jti": "unique_token_id_for_revocation"
}
```

**Cấu hình JWT:**

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| Algorithm | HS256 | HMAC với SHA-256 |
| Access Token TTL | 15 phút | Ngắn hạn, giảm rủi ro nếu bị lộ |
| Refresh Token TTL | 7 ngày | Dài hạn hơn cho user experience |
| Refresh Token Rotation | Mỗi lần refresh tạo token mới | Chống replay attack |
| Issuer | `ai-sdlc-system` | Xác định nguồn token |
| Audience | `ai-sdlc-api` | Xác định đích token |

**Refresh Token Rotation:**
- Mỗi lần refresh tạo refresh token mới, cũ bị vô hiệu hóa
- Lưu `jti` (JWT ID) vào database để track và revoke
- Nếu phát hiện refresh token đã bị used → revoke toàn bộ family (tất cả token thuộc cùng user session)

### 1.2 API Key Authentication cho Agent-to-Agent Communication

Agent giao tiếp nội bộ sử dụng API Key thay vì JWT để tránh overhead và hỗ trợ long-running processes.

**Flow:**
```
Agent Process → POST /api/v1/tasks/{id}/transition
               Headers: X-API-Key: aislk_live_xxxx...
               ← 200 OK
```

**API Key Format:**
```
aislk_{env}_{random32chars}
```

Ví dụ: `aislk_live_abc123def456ghi789jkl012mno345pqr678`

**API Key Properties:**

| Thuộc tính | Giá trị |
|---|---|
| Prefix | `aislk_live_` hoặc `aislk_test_` |
| Length | 44 characters tổng cộng |
| Hash algorithm | SHA-256 |
| Storage | Chỉ lưu `key_hash` (SHA-256) và `key_prefix` trong DB |
| Display | Key gốc chỉ hiển thị 1 lần khi tạo |

**API Key Lifecycle:**
1. **Tạo**: Admin tạo key qua `POST /api/v1/api-keys`, hệ thống trả key gốc 1 lần duy nhất
2. **Sử dụng**: Agent gửi key trong header `X-API-Key: <key>`
3. **Verify**: API hash key với SHA-256, so với `key_hash` trong DB
4. **Thu hồi**: Admin vô hiệu hóa key qua `PATCH /api/v1/api-keys/{id}` → `is_active = false`
5. **Xoá**: Soft delete hoặc hard delete tuỳ policy

### 1.3 Database Schema

**Users Table** (đã có trong `schema.sql`):

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,  -- bcrypt hash
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',  -- admin, operator, developer, viewer
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**API Keys Table** (đã có trong `schema.sql`):

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,          -- Tên mô tả, vd: "gatekeeper-agent-key"
    key_hash VARCHAR(255) NOT NULL,     -- SHA-256 hash của key gốc
    key_prefix VARCHAR(20) NOT NULL,     -- 8 ký tự đầu để identify, vd: "aislk_li"
    permissions JSONB DEFAULT '["read"]', -- Permissions gắn với key
    expires_at TIMESTAMP WITH TIME ZONE,  -- Thời hạn key
    last_used_at TIMESTAMP WITH TIME ZONE, -- Lần sử dụng gần nhất
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.4 Password Hashing

Sử dụng **bcrypt** với cost factor 12:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Hash password khi tạo user
hashed = pwd_context.hash(plain_password)

# Verify password khi login
is_valid = pwd_context.verify(plain_password, hashed)

# Auto-upgrade nếu cost factor cũ thấp hơn
if pwd_context.needs_update(hashed):
    new_hash = pwd_context.hash(plain_password)
    # Update hash trong DB
```

**Lý do chọn bcrypt:**
- Adaptive cost factor — chống brute force
- Salt tự động — chống rainbow table
- Built-in trong PassLib — dễ tích hợp Python/FastAPI
- Cost factor 12 — cân bằng giữa bảo mật và hiệu năng (~250ms/hash)

### 1.5 Token Expiration và Refresh

**Token Lifecycle:**

```
┌─────────────┐     Login      ┌──────────────────────┐
│   Client     │ ───────────────→ │  POST /auth/login   │
└─────────────┘                  └──────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  Access Token (15m)   │
                              │  Refresh Token (7d)    │
                              └──────────────────────┘
                                         │
                     ┌───────────────────┼───────────────────┐
                     │                   │                   │
                     ▼                   ▼                   ▼
              ┌─────────────┐   ┌─────────────────┐  ┌─────────────┐
              │  API Call    │   │  Token Expired   │  │  Refresh    │
              │  with Token  │   │  (401 Response)  │  │  Flow       │
              └─────────────┘   └─────────────────┘  └─────────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────────┐
                                                │ POST /auth/refresh  │
                                                │ → New Access Token  │
                                                │ → New Refresh Token │
                                                └─────────────────────┘
```

**Quy tắc expiration:**

| Token Type | TTL | Action khi hết hạn |
|---|---|---|
| Access Token | 15 phút | Client dùng refresh token lấy access token mới |
| Refresh Token | 7 ngày | User phải login lại |
| API Key | Tuỳ config (`expires_at`) | Tạo API key mới |

**Token Revocation:**
- Refresh token: Lưu `jti` vào `revoked_tokens` table, check khi refresh
- Access token: Không revoke trực tiếp (stateless), dựa vào short TTL
- API key: Set `is_active = false` trong `api_keys` table

**Bảng revoked_tokens (thêm mới):**

```sql
CREATE TABLE revoked_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jti VARCHAR(255) NOT NULL UNIQUE,
    token_type VARCHAR(50) NOT NULL DEFAULT 'refresh',
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_revoked_tokens_jti ON revoked_tokens(jti);
CREATE INDEX idx_revoked_tokens_expires_at ON revoked_tokens(expires_at);
```

**Cleanup job:** Periodically delete expired entries từ `revoked_tokens` (entries có `expires_at < NOW()`).

---

## 2. Authorization / RBAC

### 2.1 Role Definitions

Hệ thống định nghĩa 4 roles với cấp quyền tăng dần:

| Role | Mô tả | Phạm vi |
|---|---|---|
| `viewer` | Chỉ xem, không sửa | Đọc project/task, không tạo/sửa/xoá |
| `developer` | Phát triển task, không quản trị | Tạo/sửa task trong project được gán |
| `operator` | Vận hành hệ thống, quản lý agent | Tất cả thao tác trừ user management |
| `admin` | Toàn quyền | Tất cả thao tác, bao gồm user và system management |

### 2.2 Role Permissions Matrix

| Resource / Action | `viewer` | `developer` | `operator` | `admin` |
|---|---|---|---|---|
| **Projects** | | | | |
| List projects | ✅ | ✅ | ✅ | ✅ |
| View project detail | ✅ | ✅ | ✅ | ✅ |
| Create project | ❌ | ✅ | ✅ | ✅ |
| Update project | ❌ | ✅ (assigned) | ✅ | ✅ |
| Delete project | ❌ | ❌ | ✅ | ✅ |
| **Tasks** | | | | |
| List tasks | ✅ (assigned) | ✅ | ✅ | ✅ |
| View task detail | ✅ (assigned) | ✅ | ✅ | ✅ |
| Create task | ❌ | ✅ (assigned) | ✅ | ✅ |
| Update task | ❌ | ✅ (assigned) | ✅ | ✅ |
| Transition task state | ❌ | ❌ | ✅ | ✅ |
| Cancel task | ❌ | ✅ (own) | ✅ | ✅ |
| **Agent Operations** | | | | |
| Trigger agent | ❌ | ❌ | ✅ | ✅ |
| View agent logs | ✅ | ✅ | ✅ | ✅ |
| Override agent decision | ❌ | ❌ | ❌ | ✅ |
| **Audit Logs** | | | | |
| View audit logs | ✅ (own project) | ✅ | ✅ | ✅ |
| Export audit logs | ❌ | ❌ | ✅ | ✅ |
| **Cost Tracking** | | | | |
| View cost summary | ❌ | ❌ | ✅ | ✅ |
| View detailed costs | ❌ | ❌ | ✅ | ✅ |
| **Deployments** | | | | |
| Deploy staging | ❌ | ❌ | ✅ | ✅ |
| Deploy production | ❌ | ❌ | ❌ | ✅ (LAW-004) |
| Rollback deployment | ❌ | ❌ | ✅ | ✅ |
| **User Management** | | | | |
| List users | ❌ | ❌ | ✅ | ✅ |
| Create/update users | ❌ | ❌ | ❌ | ✅ |
| Assign roles | ❌ | ❌ | ❌ | ✅ |
| **API Keys** | | | | |
| Create API key (own) | ❌ | ✅ | ✅ | ✅ |
| Revoke API key (own) | ❌ | ✅ | ✅ | ✅ |
| Manage all API keys | ❌ | ❌ | ❌ | ✅ |
| **System Config** | | | | |
| View config | ❌ | ❌ | ✅ | ✅ |
| Update config | ❌ | ❌ | ❌ | ✅ |
| Manage circuit breaker | ❌ | ❌ | ✅ | ✅ |

### 2.3 Per-Project Permissions

User có thể được gán vào project với role cụ thể, khác với global role:

```sql
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'developer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
```

**Quy tắc:**
- Global role xác định quyền system-wide (tạo user, manage API keys, v.v.)
- Project role xác định quyền trong project cụ thể (tạo task, deploy, v.v.)
- Effective permission = max(global_role_permission, project_role_permission)
- `admin` luôn có toàn quyền tất cả projects
- `viewer` không thể có project role cao hơn `developer`

### 2.4 Agent Permissions

Mỗi agent có permission boundary rõ ràng:

| Agent | Đọc | Ghi | Xóa | Đặc biệt |
|---|---|---|---|---|
| **Gatekeeper** | Tasks, Memory | Task status (NEW → ANALYZING) | ❌ | Chỉ phân loại, không modify code |
| **Orchestrator** | Tasks, Projects, Modules | Task status, Task breakdown, Dependencies | ❌ | Không được directly implement |
| **Specialist** | Tasks, Code repos, Memory | Code files, Test files, Docs | ❌ | Chỉ trong scope task assigned |
| **Auditor** | Code, Tests, Spec | Audit logs, Verdict, Scores | ❌ | Không được modify code |
| **Mentor** | All tasks, History, Memory | Decisions, Verdict, Lesson learned | ❌ | Chiến lược, override other agents |
| **DevOps** | Deployment configs, Code | Build logs, Deploy status, Containers | Old containers (cleanup) | Không được modify source code |
| **Monitoring** | Logs, Metrics, Feedback | Alerts, Error reports, Bug reports | Old logs (retention) | Chỉ observe, không modify state |

**Agent API Key Permissions:**

```json
{
  "gatekeeper": ["read:tasks", "write:task_status", "read:memory"],
  "orchestrator": ["read:tasks", "read:projects", "read:modules", "write:task_status", "write:task_breakdown", "write:dependencies"],
  "specialist": ["read:tasks", "read:code", "read:memory", "write:code", "write:tests", "write:docs"],
  "auditor": ["read:tasks", "read:code", "read:tests", "read:spec", "write:audit_logs", "write:verdict"],
  "mentor": ["read:all", "write:decisions", "write:verdict", "write:memory"],
  "devops": ["read:tasks", "read:code", "read:configs", "write:deployments", "write:containers"],
  "monitoring": ["read:logs", "read:metrics", "write:alerts", "write:reports"]
}
```

---

## 3. API Security

### 3.1 Rate Limiting

**Per-User Rate Limits:**

| Endpoint Category | Viewer | Developer | Operator | Admin |
|---|---|---|---|---|
| Read endpoints | 100 req/min | 200 req/min | 500 req/min | 500 req/min |
| Write endpoints | N/A | 50 req/min | 100 req/min | 200 req/min |
| Auth endpoints | 5 req/min | 5 req/min | 5 req/min | 5 req/min |
| AI/LLM endpoints | N/A | 10 req/min | 30 req/min | 30 req/min |

**Per-Agent Rate Limits:**

| Agent | Requests/min | Burst | Ghi chú |
|---|---|---|---|
| Gatekeeper | 60 | 10 | Xử lý request phân loại |
| Orchestrator | 30 | 5 | Điều phối workflow |
| Specialist | 20 | 3 | Thực thi code |
| Auditor | 30 | 5 | Review và audit |
| Mentor | 10 | 2 | Giới hạn bởi quota (LAW-017) |
| DevOps | 15 | 3 | Build và deploy |
| Monitoring | 60 | 10 | Continuous monitoring |

**Implementation:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Per-endpoint rate limit
@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request):
    ...

# Per-user rate limit (dựa trên user_id từ JWT)
@app.get("/api/v1/tasks")
@limiter.limit("200/minute")
async def list_tasks(request: Request, user: User = Depends(get_current_user)):
    ...

# Per-agent rate limit (dựa trên API key)
@app.post("/api/v1/tasks/{task_id}/transition")
@limiter.limit("30/minute", key_func=get_api_key_id)
async def transition_task(task_id: str, ...):
    ...
```

**Rate Limit Headers:**

```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 187
X-RateLimit-Reset: 1716198000
Retry-After: 30  (khi 429 Too Many Requests)
```

### 3.2 Input Validation

Tất cả API input được validate bằng **Pydantic models** (tuân thủ LAW-002):

```python
from pydantic import BaseModel, Field, validator, constr
from datetime import datetime
from typing import Optional
import re

class TaskCreateRequest(BaseModel):
    title: constr(min_length=1, max_length=500) = Field(
        ..., description="Task title"
    )
    description: Optional[constr(max_length=10000)] = Field(
        None, description="Task description"
    )
    priority: constr(regex=r'^(LOW|MEDIUM|HIGH|CRITICAL)$') = Field(
        default="MEDIUM"
    )
    module_id: Optional[str] = Field(
        None, description="Module UUID"
    )

    @validator('title')
    def sanitize_title(cls, v):
        # Loại bỏ XSS patterns
        v = re.sub(r'<[^>]*>', '', v)
        return v.strip()

class TaskTransitionRequest(BaseModel):
    new_status: constr(regex=r'^(NEW|ANALYZING|PLANNING|IMPLEMENTING|VERIFYING|REVIEWING|DONE|ESCALATED|BLOCKED|FAILED|CANCELLED)$')
    reason: constr(min_length=1, max_length=2000)
    actor: constr(min_length=1, max_length=100)

class UserCreateRequest(BaseModel):
    username: constr(min_length=3, max_length=100, regex=r'^[a-zA-Z0-9_-]+$')
    email: constr(regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: constr(min_length=8, max_length=128)
    full_name: Optional[constr(max_length=255)] = None
    role: constr(regex=r'^(admin|operator|developer|viewer)$') = 'viewer'

    @validator('password')
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v
```

**Validation Rules:**
- Tất cả string input có `max_length` — chống buffer overflow
- Regex validation cho enum fields — chống invalid values
- HTML tag stripping — chống XSS trong text fields
- UUID format validation cho reference fields
- Password strength validation — minimum 8 ký tự, có uppercase, lowercase, digit, special char

### 3.3 Output Sanization

```python
def sanitize_output(data: dict) -> dict:
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = escape_html(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_output(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_output(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized

# Sensitive fields không bao giờ trả về client
EXCLUDED_FIELDS = {
    'hashed_password',
    'key_hash',
    'secret',
    'token',
    'api_key',
}

def filter_sensitive_fields(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in EXCLUDED_FIELDS}
```

**Quy tắc:**
- Không bao giờ trả `hashed_password`, `key_hash` trong API responses
- API key chỉ trả về 1 lần khi tạo, sau đó chỉ hiển thị `key_prefix`
- Error messages không lộ internal implementation details
- Stack traces chỉ hiển thị trong_dev mode, production trả generic error

### 3.4 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = {
    "production": [
        "https://ai-sdlc.example.com",
        "https://app.ai-sdlc.example.com",
    ],
    "staging": [
        "https://staging.ai-sdlc.example.com",
    ],
    "development": [
        "http://localhost:3000",
        "http://localhost:5173",
    ],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS[os.getenv("ENVIRONMENT", "development")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "X-API-Key", "Content-Type"],
    max_age=600,
)
```

**Production Rules:**
- `allow_origins`: Chỉ whitelist specific domains, **không dùng `*`**
- `allow_credentials`: `True` (cần cho JWT cookie)
- `allow_methods`: Chỉ cho phép methods cần thiết
- `allow_headers`: Chỉ cho phép headers cần thiết
- `max_age`: 600 giây (preflight cache)

### 3.5 Security Headers

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

| Header | Giá trị | Mục đích |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Chóng MIME type sniffing |
| `X-Frame-Options` | `DENY` | Chóng clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Chóng XSS trong older browsers |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Giới hạn referrer info |
| `Content-Security-Policy` | Whitelist specific sources | Chóng XSS, injection |
| `Permissions-Policy` | Disable camera, mic, geo | Giới hạn browser features |
| `Strict-Transport-Security` | `max-age=31536000` | Chóng downgrade attacks (HTTPS only) |

---

## 4. Secret Management

### 4.1 Environment Variables cho tất cả Secrets

**Nguny tắc:** Mọi secret phải đến từ environment variables, **không bao giờ** hardcoded trong source code (LAW-005).

**Danh sách environment variables:**

| Variable | Mô tả | Required | Default |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | ✅ | — |
| `JWT_SECRET_KEY` | Khý.sign JWT | ✅ | — |
| `JWT_ALGORITHM` | Algorithm sign JWT | ❌ | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access token (phút) | ❌ | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | TTL refresh token (ngày) | ❌ | `7` |
| `BCRYPT_ROUNDS` | Cost factor cho bcrypt | ❌ | `12` |
| `OPENAI_API_KEY` | OpenAI API key (embeddings) | ❌ | — |
| `DEEPSEEK_API_KEY` | DeepSeek API key | ✅ | — |
| `QWEN_API_KEY` | Qwen (Alibaba) API key | ✅ | — |
| `REDIS_URL` | Redis connection cho rate limiting | ❌ | `redis://localhost:6379` |
| `CORS_ORIGINS` | Comma-separated allowed origins | ❌ | `http://localhost:3000` |
| `ENVIRONMENT` | `development` / `staging` / `production` | ✅ | `development` |
| `LOG_LEVEL` | Logging level | ❌ | `INFO` |
| `MENTOR_DAILY_QUOTA` | Giới hạn Mentor calls/ngày | ❌ | `10` |
| `LLM_TIMEOUT_SECONDS` | Timeout cho LLM calls | ❌ | `120` |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Số failure trước khi mở circuit | ❌ | `5` |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | Thời gian chờ trước half-open (giây) | ❌ | `60` |
| `SMTP_HOST` | Email server host | ❌ | — |
| `SMTP_PORT` | Email server port | ❌ | `587` |
| `SMTP_USER` | Email user | ❌ | — |
| `SMTP_PASSWORD` | Email password | ❌ | — |

### 4.2 Không Hardcoded Secrets (LAW-005)

**Enforcement:**

```yaml
# Pre-commit hook / CI check
rules:
  - id: no-hardcoded-secrets
    patterns:
      - pattern: |
          password = "..."
      - pattern: |
          api_key = "..."
      - pattern: |
          secret = "..."
      - pattern: |
          token = "sk-..."
      - pattern: |
          token = "aislk_..."
    message: "LAW-005: No hardcoded secrets. Use environment variables."
```

**Code Review Rules:**
1. Không commit `.env` files (đã có trong `.gitignore`)
2. Secret scanners (truffleHog, gitleaks) chạy trong CI pipeline
3. Pre-commit hooks kiểm tra hardcoded patterns
4. Audit log không bao giờ log raw secret values

### 4.3 .env.example Template

```env
# ============================================================
# AI SDLC System - Environment Variables Template
# Copy this file to .env and fill in the values
# NEVER commit .env to version control
# ============================================================

# ---- Database ----
DATABASE_URL=postgresql://ai_sdlc:change_me@localhost:5432/ai_sdlc_db

# ---- JWT Authentication ----
JWT_SECRET_KEY=change-me-to-a-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12

# ---- LLM API Keys ----
OPENAI_API_KEY=sk-openai-api-key-here
DEEPSEEK_API_KEY=sk-deepseek-api-key-here
QWEN_API_KEY=sk-qwen-api-key-here

# ---- Redis (Rate Limiting) ----
REDIS_URL=redis://localhost:6379/0

# ---- CORS ----
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ---- Environment ----
ENVIRONMENT=development
LOG_LEVEL=INFO

# ---- Agent Configuration ----
MENTOR_DAILY_QUOTA=10
LLM_TIMEOUT_SECONDS=120
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# ---- Email (Optional) ----
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# ---- Docker Deployment (Optional) ----
DOCKER_REGISTRY=ghcr.io/your-org
DOCKER_REGISTRY_USERNAME=
DOCKER_REGISTRY_PASSWORD=
```

### 4.4 Secret Rotation Policy

**Rotation Schedule:**

| Secret Type | Rotation Frequency | Process |
|---|---|---|
| JWT Secret Key | 90 ngày | Generate mới, deploy zero-downtime với graceful key rotation |
| Database Password | 90 ngày | Rotate qua PostgreSQL, update `DATABASE_URL` |
| API Keys (LLM) | Khi cần | Revoke cũ, tạo mới, update env var |
| API Keys (System) | 90 ngày | Revoke qua admin panel, tạo mới |
| Refresh Tokens | 7 ngày (auto) | Auto-rotation mỗi lần refresh |
| API Keys (Agent) | 1 năm hoặc khi compromise | Tạo mới, revoke cũ |

**JWT Key Rotation (Zero Downtime):**
- Giai đoạn 1: Deploy với `JWT_SECRET_KEY` mới + `JWT_PREVIOUS_SECRET_KEY` cũ
- Giai đoạn 2: Access tokens cũ vẫn hoạt động (verify bằng previous key)
- Giai đoạn 3: Sau khi tất cả access tokens cũ hết hạn (15 phút), remove previous key
- Total window: ~30 phút (15 phút TTL + buffer)

```python
# JWT Key Rotation Support
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_PREVIOUS_SECRET_KEY = os.getenv("JWT_PREVIOUS_SECRET_KEY", "")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        if JWT_PREVIOUS_SECRET_KEY:
            payload = jwt.decode(token, JWT_PREVIOUS_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        raise
```

### 4.5 LLM API Keys Management

**Cấu trúc quản lý:**

```python
import os
from dataclasses import dataclass

@dataclass
class LLMProvider:
    name: str
    env_key: str
    models: list[str]
    fallback_provider: str | None

PROVIDERS = [
    LLMProvider("deepseek", "DEEPSEEK_API_KEY",
                ["deepseek-v4-pro", "deepseek-v4-flash"], None),
    LLMProvider("qwen", "QWEN_API_KEY",
                ["qwen-3.5-plus", "qwen-3.6-plus"], "deepseek"),
    LLMProvider("openai", "OPENAI_API_KEY",
                ["text-embedding-3-small"], None),
]

def get_api_key(provider_name: str) -> str:
    provider = next((p for p in PROVIDERS if p.name == provider_name), None)
    if not provider:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    key = os.getenv(provider.env_key)
    if not key:
        raise ValueError(f"Missing API key: {provider.env_key}")
    return key
```

**Quy tắc:**
- LLM API keys chỉ đọc từ environment variables
- Không bao giờ log API key values (chỉ log `provider_name` và `model`)
- Circuit breaker tự động switch sang fallback provider khi primary fail (LAW-014)
- `llm_call_logs` chỉ lưu `model` và `agent_name`, **không** lưu API key
- API key validation khi startup — fail fast nếu thiếu key

---

## 5. Data Security

### 5.1 Encryption at Rest

**Database Encryption:**

| Layer | Phương pháp | Scope |
|---|---|---|
| Disk-level | LUKS / EBS Encryption | Toàn bộ disk volume |
| Table-level | `pgcrypto` extension | Sột nhạy cảm (PII) |
| Column-level | `AES-256` encrypt/decrypt functions | Email, full_name, API keys |
| Backup | `pg_dump` + `gpg` encryption | Automated backup |

**Column-Level Encryption:**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive columns
-- Email stored as encrypted text
CREATE OR REPLACE FUNCTION encrypt_pii(data TEXT, key TEXT)
RETURNS TEXT AS $$
    SELECT encode(pgp_sym_encrypt(data, key), 'hex');
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION decrypt_pii(data TEXT, key TEXT)
RETURNS TEXT AS $$
    SELECT pgp_sym_decrypt(decode(data, 'hex'), key);
$$ LANGUAGE SQL;

-- Example: encrypt user email on insert
-- INSERT INTO users (..., email, ...) VALUES (..., encrypt_pii('user@example.com', current_setting('app.encryption_key')), ...)
```

**Encrypted Columns:**

| Table | Column | Method |
|---|---|---|
| `users` | `email` | pgcrypto AES-256 |
| `users` | `hashed_password` | bcrypt (already hashed) |
| `api_keys` | `key_hash` | SHA-256 (already hashed) |
| `audit_logs` | `message` (if contains PII) | pgcrypto AES-256 |

### 5.2 Encryption in Transit (TLS)

**TLS Configuration:**

```
Client ←→ Load Balancer:  TLS 1.3
Load Balancer ←→ API Server: TLS 1.2+ (internal network)
API Server ←→ PostgreSQL:  TLS 1.2+ (verify-cert)
API Server ←→ Redis:       TLS 1.2+ (if Redis over network)
Agent ←→ LLM API:          TLS 1.2+ (enforced)
```

**Minimum TLS Version:** 1.2 (1.3 preferred)

**Certificate Management:**
- Production: Let's Encrypt hoặc tổ chức CA, auto-renewal
- Internal services: Self-signed CA với custom trust chain
- Database: Require SSL, `verify-full` mode

```python
# PostgreSQL connection with SSL
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=verify-full"

# Redis connection with SSL
REDIS_URL = "rediss://host:6379/0"  # rediss:// = TLS
```

### 5.3 PII Handling

**PII Classification:**

| Loại Data | Ví dụ | Classification | Storage |
|---|---|---|---|
| **Direct Identifier** | Email, username, full_name | PII-HIGH | Encrypted at rest |
| **Quasi-Identifier** | IP address, login time | PII-MEDIUM | Anonymized in logs |
| **Non-PII** | Project name, task title, code | NON-PII | Plain text |

**Handling Rules:**
1. **Email**: Encrypt khi lưu DB, decrypt chỉ khi cần hiển thị
2. **Password**: Chỉ lưu bcrypt hash, **không bao giờ** lưu plain text
3. **IP Address**: Anonymize trong logs (giữ /24 prefix, zero host bytes)
4. **Username**: Lưu plain text (cần cho auth), nhưng không xuất hiện trong audit logs lộang
5. **Full name**: Encrypt khi lưu DB

```python
import ipaddress

def anonymize_ip(ip_str: str) -> str:
    addr = ipaddress.ip_address(ip_str)
    if addr.version == 4:
        network = ipaddress.IPv4Network(f"{ip_str}/24", strict=False)
        return str(network.network_address)
    return "0.0.0.0"

# audit log: replace user IP with anonymized version
log_entry["ip"] = anonymize_ip(request.client.host)
```

**Data Export Rules:**
- Export/backup phải encrypt PII columns
- Data sharing với third parties phải anonymize trước
- Compliance: tuân thủ GDPR/CCPA data subject rights (access, deletion, portability)

### 5.4 Data Retention Policy

| Loại Data | Retention Period | Action sau expiry |
|---|---|---|
| Active tasks | Vô thời hạn (khi project active) | Archive khi project COMPLETED |
| Completed tasks | 1 năm sau project COMPLETED | Anonymize + archive |
| Failed/Cancelled tasks | 90 ngày | Delete |
| Audit logs | 3 năm | Archive to cold storage |
| Cost tracking | 2 năm | Aggregate + delete details |
| LLM call logs | 90 ngày | Delete (giữ cost summary) |
| Revoked tokens | Đến khi expire | Auto-cleanup |
| API key usage logs | 1 năm | Archive |
| Session data | 7 ngày | Delete |

**Automated Cleanup Jobs:**

```python
# Scheduled tasks (ví dụ: chạy hàng ngày lúc 3AM)
CLEANUP_JOBS = [
    # Delete expired revoked tokens
    "DELETE FROM revoked_tokens WHERE expires_at < NOW()",
    # Delete old LLM call logs (giữ cost_tracking summary)
    "DELETE FROM llm_call_logs WHERE created_at < NOW() - INTERVAL '90 days'",
    # Archive old audit logs
    "INSERT INTO audit_logs_archive SELECT * FROM audit_logs WHERE created_at < NOW() - INTERVAL '3 years'",
    "DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '3 years'",
    # Delete old failed/cancelled tasks
    "DELETE FROM tasks WHERE status IN ('FAILED', 'CANCELLED') AND updated_at < NOW() - INTERVAL '90 days'",
]
```

### 5.5 Audit Log Integrity

**Audit Log Properties:**

1. **Append-only**: Audit logs không thể sửa hoặc xoá (chỉ INSERT, không UPDATE/DELETE)
2. **Timestamped**: Mỗi entry có `created_at` timestamp
3. **Attributed**: Mỗi entry ghi `actor` và `actor_type` (user/agent/system)
4. **Hash-chained**: Mỗi entry chứa hash của entry trước để phát hiện tampering

```sql
-- Audit log integrity fields (thêm vào audit_logs table)
ALTER TABLE audit_logs ADD COLUMN prev_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN entry_hash VARCHAR(64);

-- entry_hash = SHA-256(id || action || actor || result || created_at || prev_hash)
-- Verification: check rằng mỗi entry_hash khớp với computed hash
```

**Verification Procedure:**

```python
import hashlib

def verify_audit_log_integrity(entries: list) -> bool:
    prev_hash = "0" * 64  # Genesis hash
    for entry in entries:
        # Compute expected hash
        computed = hashlib.sha256(
            f"{entry.id}{entry.action}{entry.actor}{entry.result}"
            f"{entry.created_at.isoformat()}{prev_hash}".encode()
        ).hexdigest()
        if computed != entry.entry_hash:
            return False
        prev_hash = computed
    return True
```

**Database-Level Protection:**

```sql
-- Row Security Policy: chỉ cho phép INSERT, không UPDATE/DELETE
CREATE POLICY audit_logs_insert_only ON audit_logs
    FOR INSERT TO ai_sdlc_app
    WITH CHECK (true);

-- Trigger prevent UPDATE và DELETE
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable: % operation not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_update BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

CREATE TRIGGER prevent_audit_delete BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

---

## 6. Agent Security

### 6.1 Agent Sandboxing

Mỗi agent chạy trong môi trường cách ly (sandbox) để:
- Hạn chế truy cập tài nguyên hệ thống
- Chống escalation nếu agent bị compromise
- Isolate failure domain

**Sandbox Architecture:**

```
┌──────────────────────────────────────────────────┐
│                  Host System                      │
│  ┌────────────────────────────────────────────┐  │
│  │           API Server (FastAPI)              │  │
│  └──────────────┬─────────────────────────────┘  │
│                 │                                  │
│  ┌──────────────┼─────────────────────────────┐  │
│  │         Agent Orchestrator                  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│  │  │Gatekeeper│ │Special. │ │Auditor  │      │  │
│  │  │ (process)│ │(contain.)│ │(contain.)│     │  │
│  │  └─────────┘ └─────────┘ └─────────┘      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│  │  │Mentor   │ │ DevOps  │ │Monitor  │      │  │
│  │  │(contain.)│ │(contain.)│ │(contain.)│     │  │
│  │  └─────────┘ └─────────┘ └─────────┘      │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │         Shared Services (DB, Redis, API)   │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**Dev Mode (Process Isolation):**

```python
# Mỗi agent chạy trong subprocess riêng
import multiprocessing

class AgentSandbox:
    def __init__(self, agent_config: dict):
        self.process = None
        self.config = agent_config

    def start(self):
        self.process = multiprocessing.Process(
            target=agent_entrypoint,
            args=(self.config,),
            name=f"agent-{self.config['name']}",
        )
        self.process.start()

    def stop(self, timeout=30):
        if self.process:
            self.process.terminate()
            self.process.join(timeout=timeout)
            if self.process.is_alive():
                self.process.kill()
```

**Prod Mode (Docker Container Isolation):**

```yaml
# docker-compose.yml - Agent container definition
agent-specialist:
  image: ai-sdlc-agent:latest
  container_name: agent-specialist
  restart: unless-stopped
  read_only: true
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
  networks:
    - agent-network
  environment:
    - AGENT_NAME=specialist
    - API_BASE_URL=http://api-server:8000
    - AGENT_API_KEY=${SPECIALIST_API_KEY}
  tmpfs:
    - /tmp:size=100M
  volumes:
    - agent-workspace:/workspace:rw
  logging:
    driver: json-file
    options:
      max-size: "50m"
      max-file: "3"
```

### 6.2 Agent Rate Limits

Đã mô tả trong Section 3.1. Bổ sung thêm:

**Agent-Level Quotas:**

| Agent | Max concurrent tasks | Max tasks/day | Max LLM calls/task | Max tokens/day |
|---|---|---|---|---|
| Gatekeeper | 10 | Unlimited | 5 | 100K |
| Orchestrator | 5 | 500 | 20 | 1M |
| Specialist | 3 | 100 | 50 | 5M |
| Auditor | 5 | 200 | 30 | 2M |
| Mentor | 1 | 10 (LAW-017) | 10 | 500K |
| DevOps | 2 | 50 | 20 | 1M |
| Monitoring | 1 | Unlimited | 10 | 200K |

**Enforcement:**

```python
from dataclasses import dataclass

@dataclass
class AgentQuota:
    max_concurrent: int
    max_daily_tasks: int | None
    max_llm_calls_per_task: int
    max_daily_tokens: int

AGENT_QUOTAS = {
    "gatekeeper": AgentQuota(10, None, 5, 100_000),
    "orchestrator": AgentQuota(5, 500, 20, 1_000_000),
    "specialist": AgentQuota(3, 100, 50, 5_000_000),
    "auditor": AgentQuota(5, 200, 30, 2_000_000),
    "mentor": AgentQuota(1, 10, 10, 500_000),
    "devops": AgentQuota(2, 50, 20, 1_000_000),
    "monitoring": AgentQuota(1, None, 10, 200_000),
}

class QuotaExceededError(Exception):
    pass

def check_agent_quota(agent_name: str, task_id: str | None = None):
    quota = AGENT_QUOTAS[agent_name]
    # Check concurrent tasks
    active = count_active_tasks(agent_name)
    if active >= quota.max_concurrent:
        raise QuotaExceededError(f"Agent {agent_name}: concurrent limit {quota.max_concurrent} reached")
    # Check daily tasks
    if quota.max_daily_tasks:
        today_count = count_daily_tasks(agent_name)
        if today_count >= quota.max_daily_tasks:
            raise QuotaExceededError(f"Agent {agent_name}: daily limit {quota.max_daily_tasks} reached")
    # Check daily tokens
    today_tokens = count_daily_tokens(agent_name)
    if today_tokens >= quota.max_daily_tokens:
        raise QuotaExceededError(f"Agent {agent_name}: daily token limit {quota.max_daily_tokens} reached")
```

### 6.3 Mentor Quota Enforcement

Tuân thủ LAW-017: Mentor có daily call limit.

```sql
-- mentor_quota table (đã có trong schema.sql)
CREATE TABLE mentor_quota (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    calls_used INT NOT NULL DEFAULT 0,
    calls_limit INT NOT NULL DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date)
);
```

```python
from datetime import date
from fastapi import HTTPException

MENTOR_DAILY_LIMIT = int(os.getenv("MENTOR_DAILY_QUOTA", "10"))

async def check_mentor_quota(db: AsyncSession) -> None:
    today = date.today()
    quota = await db.execute(
        select(MentorQuota).where(MentorQuota.date == today)
    )
    entry = quota.scalar_one_or_none()

    if entry is None:
        entry = MentorQuota(date=today, calls_used=0, calls_limit=MENTOR_DAILY_LIMIT)
        db.add(entry)
        await db.commit()
        return

    if entry.calls_used >= entry.calls_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Mentor daily quota exceeded ({entry.calls_used}/{entry.calls_limit})"
        )

    entry.calls_used += 1
    await db.commit()

async def mentor_endpoint(request, db: AsyncSession):
    await check_mentor_quota(db)
    # ... proceed with Mentor logic
```

### 6.4 Agent Permissions Boundary

Mỗi agent chỉ có quyền thực hiện actions trong phạm vi được định nghĩa:

```python
from enum import Enum
from dataclasses import dataclass

class Permission(Enum):
    READ_TASKS = "read:tasks"
    WRITE_TASK_STATUS = "write:task_status"
    WRITE_TASK_BREAKDOWN = "write:task_breakdown"
    READ_CODE = "read:code"
    WRITE_CODE = "write:code"
    WRITE_TESTS = "write:tests"
    WRITE_DOCS = "write:docs"
    READ_MEMORY = "read:memory"
    WRITE_MEMORY = "write:memory"
    WRITE_AUDIT = "write:audit_logs"
    WRITE_VERDICT = "write:verdict"
    WRITE_DECISIONS = "write:decisions"
    READ_CONFIGS = "read:configs"
    WRITE_DEPLOYMENTS = "write:deployments"
    WRITE_CONTAINERS = "write:containers"
    READ_LOGS = "read:logs"
    READ_METRICS = "read:metrics"
    WRITE_ALERTS = "write:alerts"
    WRITE_REPORTS = "write:reports"
    READ_ALL = "read:all"

AGENT_PERMISSIONS = {
    "gatekeeper": [
        Permission.READ_TASKS,
        Permission.WRITE_TASK_STATUS,
        Permission.READ_MEMORY,
    ],
    "orchestrator": [
        Permission.READ_TASKS,
        Permission.READ_MEMORY,
        Permission.WRITE_TASK_STATUS,
        Permission.WRITE_TASK_BREAKDOWN,
    ],
    "specialist": [
        Permission.READ_TASKS,
        Permission.READ_CODE,
        Permission.READ_MEMORY,
        Permission.WRITE_CODE,
        Permission.WRITE_TESTS,
        Permission.WRITE_DOCS,
    ],
    "auditor": [
        Permission.READ_TASKS,
        Permission.READ_CODE,
        Permission.WRITE_AUDIT,
        Permission.WRITE_VERDICT,
    ],
    "mentor": [
        Permission.READ_ALL,
        Permission.WRITE_DECISIONS,
        Permission.WRITE_VERDICT,
        Permission.WRITE_MEMORY,
    ],
    "devops": [
        Permission.READ_TASKS,
        Permission.READ_CODE,
        Permission.READ_CONFIGS,
        Permission.WRITE_DEPLOYMENTS,
        Permission.WRITE_CONTAINERS,
    ],
    "monitoring": [
        Permission.READ_LOGS,
        Permission.READ_METRICS,
        Permission.WRITE_ALERTS,
        Permission.WRITE_REPORTS,
    ],
}

def agent_has_permission(agent_name: str, permission: Permission) -> bool:
    return permission in AGENT_PERMISSIONS.get(agent_name, [])
```

### 6.5 Resource Limits per Agent

**Per-Process Limits (Dev Mode):**

```python
import resource

def set_agent_resource_limits(agent_name: str):
    limits = AGENT_RESOURCE_LIMITS[agent_name]

    # CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))

    # Memory limit (bytes)
    resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))

    # File descriptor limit
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits.max_fds, limits.max_fds))

    # Process limit
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))  # No fork
```

| Agent | CPU (seconds/task) | Memory (MB) | File Descriptors | Process Limit |
|---|---|---|---|---|
| Gatekeeper | 30 | 256 | 64 | 1 |
| Orchestrator | 120 | 512 | 128 | 1 |
| Specialist | 600 | 2048 | 256 | 1 |
| Auditor | 180 | 512 | 128 | 1 |
| Mentor | 300 | 1024 | 128 | 1 |
| DevOps | 600 | 2048 | 256 | 1 |
| Monitoring | 60 | 256 | 64 | 1 |

**Per-Container Limits (Prod/Docker Mode):**

Đã định nghĩa trong Section 6.1 Docker Compose. Key limits:
- `cpus`: 0.5-2.0
- `memory`: 512MB - 2GB
- `read_only`: true (filesystem chỉ đọc)
- `cap_drop: ALL` (drop tất cả Linux capabilities)
- Network isolation (chỉ agent-network)

---

## 7. OpenCode Security

### 7.1 Tool Restrictions per Agent

Mỗi agent chỉ có quyền sử dụng một tập tools cụ thể:

| Tool | Gatekeeper | Orchestrator | Specialist | Auditor | Mentor | DevOps | Monitoring |
|---|---|---|---|---|---|---|---|
| `read_file` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `write_file` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `create_file` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| `delete_file` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `execute_command` | ❌ | ❌ | ✅ (restricted) | ❌ | ❌ | ✅ (restricted) | ❌ |
| `search_code` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `http_request` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (deploy) | ✅ (monitor) |
| `database_query` | ✅ (read) | ✅ (read) | ❌ | ✅ (read) | ✅ (read) | ❌ | ✅ (read) |
| `llm_call` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `state_transition` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

**Implementation:**

```python
AGENT_TOOL_ALLOWLIST = {
    "gatekeeper": ["search_code", "database_query:read", "llm_call", "state_transition"],
    "orchestrator": ["read_file", "search_code", "database_query:read", "llm_call", "state_transition"],
    "specialist": ["read_file", "write_file", "create_file", "execute_command:restricted", "search_code", "llm_call", "state_transition"],
    "auditor": ["read_file", "search_code", "database_query:read", "llm_call", "state_transition"],
    "mentor": ["read_file", "search_code", "database_query:read", "llm_call", "state_transition"],
    "devops": ["read_file", "create_file", "execute_command:restricted", "http_request:deploy", "llm_call"],
    "monitoring": ["read_file", "search_code", "database_query:read", "http_request:monitor", "llm_call"],
}

def check_tool_permission(agent_name: str, tool_name: str) -> bool:
    allowed = AGENT_TOOL_ALLOWLIST.get(agent_name, [])
    base_tool = tool_name.split(":")[0]
    return base_tool in allowed or tool_name in allowed
```

### 7.2 Command Allowlist/Blocklist (Dev Mode)

Khi chạy Dev Mode (local process), agent cần `execute_command` bị giới hạn:

**Allowlist — Commands được phép chạy:**

```python
COMMAND_ALLOWLIST = {
    "specialist": [
        "python", "pytest", "ruff", "mypy", "black", "isort",
        "pip", "poetry", "npm", "npx", "node",
        "git status", "git diff", "git log", "git branch",
        "ls", "cat", "head", "tail", "wc", "grep", "find",
        "mkdir", "cp", "mv",
    ],
    "devops": [
        "docker build", "docker push", "docker run", "docker stop",
        "docker compose", "kubectl apply", "kubectl rollout",
        "helm", "npm run build", "npm run test",
        "git status", "git diff", "git log",
        "ls", "cat", "head", "tail",
    ],
}
```

**Blocklist — Commands KHÔNG BAO GIỜ được phép:**

```python
COMMAND_BLOCKLIST = [
    # System modification
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=",
    "chmod 777", "chown root",
    # Network attacks
    "nc -l", "ncat", "nmap", "curl.*|.*bash",
    "wget.*|.*bash",
    # Privilege escalation
    "sudo", "su root", "passwd",
    # Process manipulation
    "kill -9 1", "pkill -9",
    # Data exfiltration
    "scp", "rsync.*@",
    # Package installation (unless in allowlist)
    "apt-get install", "yum install", "pip install.*--user",
    # Shell escape
    "bash -i", "sh -i", "/bin/bash -i",
    "python -c 'import os;os.system",
]
```

**Implementation:**

```python
import re
import shlex

def validate_command(agent_name: str, command: str) -> tuple[bool, str]:
    # Blocklist check first (always enforced)
    for pattern in COMMAND_BLOCKLIST:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Command blocked by security policy: matches '{pattern}'"

    # Extract base command
    try:
        parts = shlex.split(command)
        base_cmd = parts[0]
    except ValueError:
        return False, "Invalid command syntax"

    # Check allowlist for the agent
    allowed = COMMAND_ALLOWLIST.get(agent_name, [])
    for allowed_cmd in allowed:
        if command.startswith(allowed_cmd) or base_cmd == allowed_cmd.split()[0]:
            return True, "Command allowed"

    return False, f"Command '{base_cmd}' not in allowlist for agent '{agent_name}'"
```

### 7.3 Network Restrictions (Prod Mode - Docker)

Trong Prod Mode, agent chạy trong Docker container với network isolation:

**Network Architecture:**

```
┌────────────────────────────────────────────────┐
│                 Docker Network                  │
│                                                │
│  ┌──────────────┐      ┌──────────────┐       │
│  │  API Server   │◄─────│  Agent Container│     │
│  │  (port 8000)  │      │  (restricted)  │     │
│  └──────┬───────┘      └──────────────┘       │
│         │                                      │
│  ┌──────┴───────┐      ┌──────────────┐       │
│  │  PostgreSQL   │      │    Redis      │       │
│  │  (port 5432)  │      │  (port 6379)  │       │
│  └──────────────┘      └──────────────┘       │
│                                                │
│  ┌──────────────┐                             │
│  │  LLM API     │ (outbound only)             │
│  │  (external)   │                             │
│  └──────────────┘                             │
└────────────────────────────────────────────────┘
```

**Docker Network Rules:**

```yaml
networks:
  agent-network:
    driver: bridge
    internal: false  # Needs external LLM API access
    ipam:
      config:
        - subnet: 172.28.0.0/16

  # Internal-only network for DB/API (no external access)
  internal-network:
    driver: bridge
    internal: true
```

**Per-Agent Network Policy:**

| Agent | Inbound | Outbound Allowed | Outbound Blocked |
|---|---|---|---|
| Gatekeeper | API Server | PostgreSQL, Redis, LLM API | Internet, Other agents |
| Orchestrator | API Server | PostgreSQL, Redis, LLM API | Internet, Other agents |
| Specialist | API Server | PostgreSQL, Redis, LLM API, PyPI (install deps) | General Internet |
| Auditor | API Server | PostgreSQL, Redis, LLM API | Internet, Other agents |
| Mentor | API Server | PostgreSQL, Redis, LLM API | Internet, Other agents |
| DevOps | API Server | PostgreSQL, Redis, LLM API, Docker Registry | General Internet |
| Monitoring | API Server | PostgreSQL, Redis, LLM API, SMTP | General Internet |

**iptables Rules trong container:**

```bash
# Default: DROP all outbound
iptables -P OUTPUT DROP

# Allow established connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# Allow PostgreSQL (internal)
iptables -A OUTPUT -d 172.28.0.0/16 -p tcp --dport 5432 -j ACCEPT

# Allow Redis (internal)
iptables -A OUTPUT -d 172.28.0.0/16 -p tcp --dport 6379 -j ACCEPT

# Allow LLM API (specific domains only)
iptables -A OUTPUT -d api.deepseek.com -p tcp --dport 443 -j ACCEPT
iptables -A OUTPUT -d dashscope.aliyuncs.com -p tcp --dport 443 -j ACCEPT

# Allow API Server (internal)
iptables -A OUTPUT -d 172.28.0.0/16 -p tcp --dport 8000 -j ACCEPT
```

### 7.4 File Access Controls

**Path-Based Access Control:**

```python
from pathlib import Path

AGENT_PATH_POLICY = {
    "gatekeeper": {
        "read": [],
        "write": [],
    },
    "orchestrator": {
        "read": [
            "/workspace/projects/{project_id}/**",
            "/workspace/configs/**",
        ],
        "write": [],
    },
    "specialist": {
        "read": [
            "/workspace/projects/{project_id}/**",
            "/workspace/templates/**",
            "/workspace/configs/**",
        ],
        "write": [
            "/workspace/projects/{project_id}/src/**",
            "/workspace/projects/{project_id}/tests/**",
            "/workspace/projects/{project_id}/docs/**",
        ],
    },
    "auditor": {
        "read": [
            "/workspace/projects/{project_id}/**",
            "/workspace/governance/**",
        ],
        "write": [
            "/workspace/projects/{project_id}/audit/**",
        ],
    },
    "mentor": {
        "read": ["/workspace/**"],
        "write": [
            "/workspace/projects/{project_id}/decisions/**",
            "/workspace/memory/**",
        ],
    },
    "devops": {
        "read": [
            "/workspace/projects/{project_id}/**",
            "/workspace/configs/deploy/**",
        ],
        "write": [
            "/workspace/projects/{project_id}/deploy/**",
        ],
    },
    "monitoring": {
        "read": [
            "/workspace/logs/**",
            "/workspace/configs/monitoring/**",
        ],
        "write": [
            "/workspace/logs/reports/**",
        ],
    },
}

# Paths luôn bị block
BLOCKED_PATHS = [
    "/etc/",
    "/root/",
    "/home/",
    "/var/log/auth*",
    "/var/log/syslog*",
    "**/.env",
    "**/.env.*",
    "**/credentials*",
    "**/secrets*",
    "**/*secret*",
    "**/*password*",
    "**/*token*",
    "**/*.pem",
    "**/*.key",
]

def check_path_access(agent_name: str, path: str, mode: str) -> bool:
    path_obj = Path(path)

    # Check blocked paths first
    for pattern in BLOCKED_PATHS:
        if path_obj.match(pattern):
            return False

    # Check if path contains secrets
    sensitive_keywords = ["secret", "password", "token", "credential", "key", "cert"]
    path_lower = path.lower()
    for keyword in sensitive_keywords:
        if keyword in path_lower and not path.endswith((".py", ".js", ".ts")):
            return False

    # Check agent-specific policy
    policy = AGENT_PATH_POLICY.get(agent_name, {})
    allowed = policy.get(mode, [])

    # Resolve {project_id} placeholder
    for pattern in allowed:
        if fnmatch.fnmatch(path, pattern):
            return True

    return False
```

---

## 8. Threat Model

### 8.1 Threats Table

| # | Attack Vector | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| T1 | **JWT token theft** | High | Medium | Unauthorized access to all endpoints | Short TTL (15min), rotate refresh tokens, HTTPS only, httpOnly cookies |
| T2 | **API key leakage** | Critical | Medium | Agent impersonation, unauthorized actions | SHA-256 hash storage, show once, automatic rotation, rate limiting |
| T3 | **SQL Injection** | High | Low | Data breach, data manipulation | Pydantic validation (LAW-002), parameterized queries, SQLAlchemy ORM |
| T4 | **XSS (Cross-Site Scripting)** | Medium | Medium | Session hijacking, data theft | Input sanitization, CSP headers, output escaping |
| T5 | **CSRF (Cross-Site Request Forgery)** | Medium | Low | Unauthorized state transitions | SameSite cookies, CSRF tokens, custom headers required |
| T6 | **Agent privilege escalation** | High | Low | Agent performs actions outside scope | Permission boundary enforcement, tool allowlists, RBAC checks |
| T7 | **LLM prompt injection** | Critical | Medium | Agent makes unauthorized decisions | Input sanitization, output validation, human approval for critical actions (LAW-004) |
| T8 | **Rate limit bypass** | Medium | Medium | Resource exhaustion, cost spiral | Per-user and per-agent rate limiting, progressive backoff, circuit breaker |
| T9 | **Secret exposure in logs** | High | Medium | Credentials compromised | Log sanitization, no secret logging, structured logging |
| T10 | **Mentor quota bypass** | Medium | Low | Excessive LLM costs, resource drain | Server-side quota enforcement (mentor_quota table), rate limiting |
| T11 | **Audit log tampering** | Critical | Low | Loss of accountability, cover tracks | Hash-chained entries, INSERT-only policy, database triggers block UPDATE/DELETE |
| T12 | **Container escape** | Critical | Low | Host system compromise | Read-only filesystem, cap_drop ALL, network isolation, seccomp profiles |
| T13 | **Dependency vulnerability** | Medium | High | Known CVEs in libraries | Automated dependency scanning (Dependabot/Snyk), pin versions, regular updates |
| T14 | **Man-in-the-Middle** | High | Low (with TLS) | Data interception, credential theft | TLS 1.2+ mandatory, HSTS headers, certificate pinning for internal calls |
| T15 | **Brute force login** | Medium | Medium | Account takeover | bcrypt cost factor 12, rate limiting (5 req/min), account lockout after 5 failures |
| T16 | **Data exfiltration via agent** | High | Low | Source code or data leaked externally | Network egress restrictions, file access controls, audit logging |
| T17 | **Denial of Service (DoS)** | Medium | Medium | Service unavailable | Rate limiting, circuit breaker (LAW-014), auto-scaling, Redis throttling |
| T18 | **Insider threat** | High | Low | Malicious admin actions | Audit logging, separation of duties, MFA for admin, review required for production deploy |

### 8.2 Attack Surface Analysis

**External Attack Surface:**

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERNET                                 │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Web UI       │  │  API Gateway  │  │  Webhooks     │       │
│  │  (React SPA)  │  │  (FastAPI)    │  │  (GitHub,     │       │
│  │              │  │              │  │   CI/CD)      │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │               │
│  ┌──────┴──────────────────┴──────────────────┴──────┐       │
│  │            WAF / Load Balancer (TLS termination)   │       │
│  └────────────────────────┬──────────────────────────┘       │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
┌───────────────────────────┼───────────────────────────────────┐
│                  INTERNAL NETWORK                             │
│                           │                                   │
│  ┌────────────────────────┴────────────────────────┐         │
│  │              API Server (FastAPI)                 │         │
│  │  ┌──────────────────────────────────────────┐   │         │
│  │  │  Auth Layer (JWT + API Key)               │   │         │
│  │  │  Rate Limiting Layer                       │   │         │
│  │  │  Validation Layer (Pydantic)              │   │         │
│  │  │  RBAC Layer                                │   │         │
│  │  └──────────────────────────────────────────┘   │         │
│  └──┬────────────┬────────────┬─────────────────────┘         │
│     │            │            │                               │
│  ┌──┴──┐  ┌─────┴──┐  ┌────┴─────┐  ┌──────────────┐        │
│  │ DB  │  │ Redis  │  │  Agents   │  │  LLM APIs    │        │
│  │     │  │        │  │ (sandbox) │  │  (external)  │        │
│  └─────┘  └────────┘  └──────────┘  └──────────────┘        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Attack Surface Components:**

| Component | Type | Exposure | Attack Vectors |
|---|---|---|---|
| Web UI | Frontend | Internet | XSS, CSRF, UI manipulation |
| API Gateway | Backend | Internet (via WAF) | Injection, auth bypass, rate abuse |
| Webhooks | Inbound | Internet (via WAF) | Replay attacks, payload manipulation |
| Authentication | Service | Internal | Brute force, token theft |
| Agent Containers | Service | Internal | Container escape, privilege escalation |
| Database | Storage | Internal | SQL injection (via app), data exfiltration |
| Redis | Cache | Internal | Data leakage, cache poisoning |
| LLM APIs | External | Internet (outbound) | Prompt injection, data leakage, cost abuse |
| CI/CD Pipeline | Infrastructure | External | Supply chain attack, credential exposure |

### 8.3 Trust Boundaries

```
┌───────────────────────────────────────────────────────────┐
│                    TRUST LEVEL 0: UNTRUSTED                  │
│                  (Internet, Web Browser)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              TRUST LEVEL 1: WAF / EDGE               │   │
│  │       (TLS termination, rate limiting, WAF rules)    │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │         TRUST LEVEL 2: AUTHENTICATED          │   │   │
│  │  │  (Users with valid JWT/API Key)               │   │   │
│  │  │  ┌─────────────────────────────────────┐    │   │   │
│  │  │  │     TRUST LEVEL 3: AUTHORIZED         │    │   │   │
│  │  │  │     (Users with correct RBAC role)     │    │   │   │
│  │  │  │  ┌─────────────────────────────┐   │    │   │   │
│  │  │  │  │   TRUST LEVEL 4: AGENT         │   │    │   │   │
│  │  │  │  │   (Agents in sandbox with       │   │    │   │   │
│  │  │  │  │    specific permissions)         │   │    │   │   │
│  │  │  │  │  ┌─────────────────────────┐ │   │    │   │   │
│  │  │  │  │  │  TRUST LEVEL 5: INTERNAL │ │   │    │   │   │
│  │  │  │  │  │  (DB, Redis, internal API)│ │   │    │   │   │
│  │  │  │  │  └─────────────────────────┘ │   │    │   │   │
│  │  │  │  └─────────────────────────────┘   │    │   │   │
│  │  │  └─────────────────────────────────────┘    │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

**Trust Boundary Rules:**

| Boundary | From | To | Rules |
|---|---|---|---|
| B0→B1 | Internet | WAF | TLS required, WAF rules, rate limit |
| B1→B2 | WAF | Auth Layer | Validate JWT/API key, reject anonymous |
| B2→B3 | Authenticated | RBAC | Check role, check project membership |
| B3→B4 | User | Agent | Tool restrictions, path restrictions, command blocklist |
| B4→B5 | Agent | Internal Services | Network isolation, allowed paths only |
| B5→External | Internal | LLM API | Outbound only, specific domains, circuit breaker |

**Data Flow Cross Boundaries:**

1. **User Request** (B0) → WAF (B1) → Auth (B2) → RBAC (B3) → API Handler → Response
2. **Agent Action** (B4) → Permission Check → Internal API (B5) → DB/Redis → Response
3. **LLM Call** (B4) → Circuit Breaker → External API (B5→Internet) → Sanitize Response → Agent

Mỗi lần data vượt boundary phải:
- Validate input (Pydantic schemas)
- Authenticate identity (JWT/API Key)
- Authorize action (RBAC/permissions)
- Sanitize output (remove sensitive data)
- Log audit trail (actor, action, result, timestamp)

---

## Metadata

- **Version**: 1.0.0
- **Created**: 2026-05-14
- **Last Updated**: 2026-05-14
- **Related Documents**:
  - `database/schema.sql` — Auth tables (users, api_keys)
  - `governance/laws.yaml` — LAW-005 (No hardcoded secrets), LAW-013 (Auth required)
  - `docs/agent-matrix.md` — Agent definitions và responsibilities
  - `docs/state-machine.md` — Task state transitions