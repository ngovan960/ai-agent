# Security Design

## AI SDLC Orchestrator — Authentication, Authorization & API Security

---

## 1. Authentication

### Methods
| Method | Usage | Header |
|--------|-------|--------|
| JWT Bearer Token | User authentication | `Authorization: Bearer <token>` |
| API Key | Service-to-service authentication | `X-API-Key: <key>` |

### JWT Configuration
| Parameter | Value |
|-----------|-------|
| Algorithm | HS256 |
| Token expiry | 30 minutes |
| Secret key | Environment variable (`SECRET_KEY`) |

### API Key Management
- Keys stored as hashes in `api_keys` table
- Key prefix stored for identification
- Permissions stored as JSON
- Expiry date configurable

---

## 2. Authorization

### Roles
| Role | Permissions |
|------|-------------|
| `admin` | Full access: create, read, update, delete, deploy |
| `developer` | Create tasks, read projects, execute tasks |
| `viewer` | Read-only access to projects, tasks, audit logs |

### Permission Matrix
| Endpoint | admin | developer | viewer |
|----------|-------|-----------|--------|
| GET /projects | ✓ | ✓ | ✓ |
| POST /projects | ✓ | — | — |
| PATCH /projects | ✓ | — | — |
| DELETE /projects | ✓ | — | — |
| GET /tasks | ✓ | ✓ | ✓ |
| POST /tasks | ✓ | ✓ | — |
| PATCH /tasks | ✓ | ✓ | — |
| DELETE /tasks | ✓ | — | — |
| POST /tasks/{id}/execute | ✓ | ✓ | — |
| GET /audit-logs | ✓ | ✓ | ✓ |
| GET /governance/* | ✓ | ✓ | ✓ |
| POST /governance/scan | ✓ | — | — |

---

## 3. API Security

### Input Validation
- All request bodies validated by Pydantic schemas
- String length limits enforced
- Enum values validated
- Regex patterns for specific fields

### SQL Injection Prevention
- SQLAlchemy ORM with parameterized queries
- No raw SQL in application code

### XSS Prevention
- React auto-escapes all output
- No dangerouslySetInnerHTML in dashboard

### CSRF Protection
- SameSite cookie policy
- JWT in Authorization header (not cookies)

### Rate Limiting
- Sliding window rate limiting for dashboard API
- Configurable rate limits per endpoint

---

## 4. Data Security

### Encryption
| Data | In Transit | At Rest |
|------|------------|---------|
| API traffic | TLS 1.3 | — |
| Database | — | PostgreSQL encryption |
| Secrets | — | Environment variables |
| Passwords | — | bcrypt hashing |

### Secret Management
- **LAW-005**: No hardcoded secrets
- All secrets via environment variables
- `.env` file in `.gitignore`
- `.env.example` for documentation

### Audit Trail
- **LAW-012**: All state changes must be audited
- Every API request logged (method, path, status, duration, IP)
- Every state transition logged (actor, action, result)
- Real-time WebSocket broadcast of audit events

---

## 5. Infrastructure Security

### Docker Security
- Containers run as non-root user
- Resource limits enforced (memory, CPU)
- Network isolation (separate Docker network)
- Read-only volumes where possible

### Database Security
- PostgreSQL user with limited privileges
- No direct database access from frontend
- Connection pooling with max connections

### Network Security
- API only accessible via localhost (development)
- Nginx reverse proxy for production (SSL, rate limiting)
- WebSocket connections authenticated

---

## 6. Architectural Laws (Security-Related)

| Law | Description | Severity |
|-----|-------------|----------|
| LAW-002 | All APIs must validate input | HIGH |
| LAW-004 | Critical actions require human approval | CRITICAL |
| LAW-005 | No hardcoded secrets | CRITICAL |
| LAW-013 | All API endpoints require authentication | CRITICAL |
| LAW-015 | No terminal state can be changed | CRITICAL |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
