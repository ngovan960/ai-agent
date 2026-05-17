# Database Migration

## AI SDLC Orchestrator — Database Schema & Migration Strategy

---

## Schema Overview

**Version**: 2.0.0
**Database**: PostgreSQL 16 with pgvector extension
**Total Tables**: 20
**Total Enums**: 11

---

## Tables

### Core Entities
| Table | Columns | Description |
|-------|---------|-------------|
| `users` | id, username, email, password_hash, role, created_at, updated_at | User accounts |
| `api_keys` | id, user_id, key_prefix, key_hash, name, permissions, created_at, expires_at | API authentication |
| `projects` | id, name, description, status, tech_stack, architecture, rules, created_by, created_at, updated_at | Project registry |
| `modules` | id, project_id, name, description, status, created_at, updated_at | Module registry |
| `module_dependencies` | module_id, depends_on_module_id | Module dependency junction table |

### Task System
| Table | Columns | Description |
|-------|---------|-------------|
| `tasks` | id, project_id, module_id, title, description, owner, priority, status, confidence, retries, max_retries, expected_output, risk_score, risk_level, cancellation_reason, failure_reason, created_by, created_at, updated_at, completed_at, failed_at, cancelled_at | Task registry with lifecycle |
| `task_outputs` | id, task_id, output_type, content | Task output artifacts |
| `task_dependencies` | task_id, depends_on_task_id, dependency_type | Task dependency junction table |

### Workflow & Governance
| Table | Columns | Description |
|-------|---------|-------------|
| `retries` | id, task_id, attempt_number, reason, agent_name, output, error_log, created_at | Retry tracking (max 2) |
| `audit_logs` | id, task_id, action, actor, actor_type, input, output, result, message, created_at | Complete audit trail |
| `mentor_instructions` | id, task_id, instruction_type, content, context, applied, embedding, created_at, updated_at | Mentor advice, warnings, patterns |
| `mentor_quota` | id, date, calls_used, calls_limit | Daily mentor call limits (10/day) |
| `decisions` | id, project_id, task_id, decision, reason, context, alternatives, decided_by, created_at | Architectural decisions |
| `workflows` | id, project_id, name, status, current_node, graph, state, started_at, completed_at, error, created_at | Workflow execution state |

### Deployment & Cost
| Table | Columns | Description |
|-------|---------|-------------|
| `deployments` | id, task_id, environment, image_tag, status, url, logs, deployed_by, approved_by, created_at, completed_at | Deployment records |
| `cost_tracking` | id, task_id, project_id, agent_name, model, input_tokens, output_tokens, cost_usd, latency_ms, status, error_message, created_at | LLM cost tracking |
| `llm_call_logs` | id, task_id, cost_tracking_id, agent_name, model, prompt_hash, input_tokens, output_tokens, latency_ms, status, error_message, retry_count, circuit_breaker_triggered, created_at | Detailed LLM call logs |

### Resilience & Memory
| Table | Columns | Description |
|-------|---------|-------------|
| `circuit_breaker_state` | id, model, state, failure_count, last_failure_at, last_success_at, half_open_at, created_at, updated_at | Per-model circuit breaker |
| `embedding_config` | id, model_name, provider, dimensions, cost_per_1k_input_tokens, cost_per_1k_output_tokens, is_active, created_at, updated_at | Configurable embedding dimensions |
| `law_violations` | id, task_id, law_id, law_name, severity, violation_details, location, created_at, updated_at | Architecture law violations |

---

## Enum Types

| Enum | Values |
|------|--------|
| `project_status` | ACTIVE, PAUSED, COMPLETED, ARCHIVED |
| `module_status` | PENDING, IN_PROGRESS, BLOCKED, DONE, REVIEWING |
| `task_status` | NEW, ANALYZING, PLANNING, IMPLEMENTING, VERIFYING, REVIEWING, DONE, ESCALATED, BLOCKED, FAILED, CANCELLED |
| `task_priority` | LOW, MEDIUM, HIGH, CRITICAL |
| `audit_result` | SUCCESS, FAILURE, APPROVED, REJECTED |
| `instruction_type` | advice, warning, decision, pattern |
| `risk_level` | LOW, MEDIUM, HIGH, CRITICAL |
| `deployment_env` | staging, production |
| `deployment_status` | pending, building, deploying, running, failed, rolled_back |
| `llm_call_status` | pending, completed, failed, timeout, rate_limited |
| `law_severity` | critical, high, medium |

---

## Views

### `v_task_summary`
Aggregated task statistics per project and agent.

### `v_cost_summary`
Aggregated cost statistics per project, agent, and model.

---

## Migration Strategy

### Alembic
- **Tool**: Alembic for database version control
- **Config**: `alembic.ini`, `alembic/env.py`
- **Initial migration**: Generated from `database/schema.sql`
- **Future migrations**: Auto-generated from SQLAlchemy model changes

### Commands
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Schema.sql
For fresh installations, run `database/schema.sql` directly:

```bash
docker cp database/schema.sql project-postgres-1:/tmp/schema.sql
docker exec -i project-postgres-1 psql -U ai_sdlc_user -d ai_sdlc -f /tmp/schema.sql
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `users` | idx_users_username | Fast username lookup |
| `users` | idx_users_email | Fast email lookup |
| `api_keys` | idx_api_keys_user_id | Filter keys by user |
| `api_keys` | idx_api_keys_key_prefix | Fast key prefix lookup |
| `tasks` | idx_tasks_project_id | Filter tasks by project |
| `tasks` | idx_tasks_status | Filter tasks by status |
| `tasks` | idx_tasks_created_at | Sort tasks by creation date |
| `audit_logs` | idx_audit_logs_task_id | Filter logs by task |
| `audit_logs` | idx_audit_logs_created_at | Sort logs by date |
| `cost_tracking` | idx_cost_task_id | Filter costs by task |
| `cost_tracking` | idx_cost_project_id | Filter costs by project |
| `mentor_instructions` | idx_mentor_task_id | Filter instructions by task |
| `llm_call_logs` | idx_llm_task_id | Filter logs by task |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
**Tables**: 20
**Enums**: 11
