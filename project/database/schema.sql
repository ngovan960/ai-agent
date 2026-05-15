-- ============================================================
-- AI SDLC System - Database Schema
-- PostgreSQL with pgvector extension
-- Version: 2.0.0
-- Created: 2026-05-14
-- Updated: 2026-05-14
-- Changes: Added FAILED/CANCELLED states, junction tables,
--          mentor_quota, auth tables, configurable vector dim,
--          LLM call tracking, confidence constraints
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ENUMS (v2: added FAILED, CANCELLED task statuses)
-- ============================================================

CREATE TYPE project_status AS ENUM ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED');
CREATE TYPE module_status AS ENUM ('PENDING', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'REVIEWING');
CREATE TYPE task_status AS ENUM (
    'NEW', 'ANALYZING', 'PLANNING', 'IMPLEMENTING',
    'VERIFYING', 'REVIEWING', 'DONE', 'ESCALATED', 'BLOCKED',
    'FAILED', 'CANCELLED'
);
CREATE TYPE task_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE audit_result AS ENUM ('SUCCESS', 'FAILURE', 'APPROVED', 'REJECTED');
CREATE TYPE instruction_type AS ENUM ('advice', 'warning', 'decision', 'pattern');
CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE deployment_env AS ENUM ('staging', 'production');
CREATE TYPE deployment_status AS ENUM ('pending', 'building', 'deploying', 'running', 'failed', 'rolled_back');
CREATE TYPE llm_call_status AS ENUM ('pending', 'completed', 'failed', 'timeout', 'rate_limited');

-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    permissions JSONB DEFAULT '["read"]',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);

-- ============================================================
-- PROJECTS
-- ============================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    status project_status NOT NULL DEFAULT 'ACTIVE',
    tech_stack JSONB DEFAULT '[]',
    architecture TEXT,
    rules JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_created_by ON projects(created_by);

-- ============================================================
-- MODULES
-- ============================================================

CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status module_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, name)
);

CREATE INDEX idx_modules_project_id ON modules(project_id);
CREATE INDEX idx_modules_status ON modules(status);

-- Module dependencies (junction table, replaces UUID[] array)
CREATE TABLE module_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    depends_on_module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(module_id, depends_on_module_id),
    CHECK (module_id != depends_on_module_id)
);

CREATE INDEX idx_module_dependencies_module ON module_dependencies(module_id);
CREATE INDEX idx_module_dependencies_depends ON module_dependencies(depends_on_module_id);

-- ============================================================
-- TASKS
-- ============================================================

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    owner VARCHAR(100),
    priority task_priority NOT NULL DEFAULT 'MEDIUM',
    status task_status NOT NULL DEFAULT 'NEW',
    confidence FLOAT DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    retries INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 2,
    expected_output TEXT,
    risk_score FLOAT DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 10),
    risk_level risk_level NOT NULL DEFAULT 'LOW',
    cancellation_reason TEXT,
    failure_reason TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    version INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_module_id ON tasks(module_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_owner ON tasks(owner);
CREATE INDEX idx_tasks_risk_level ON tasks(risk_level);
CREATE INDEX idx_tasks_created_by ON tasks(created_by);

-- Task outputs (separate table, replaces JSONB column for better querying)
CREATE TABLE task_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    output_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_task_outputs_task_id ON task_outputs(task_id);
CREATE INDEX idx_task_outputs_type ON task_outputs(output_type);

-- Task dependencies (junction table, replaces UUID[] array)
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'blocks',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(task_id, depends_on_task_id),
    CHECK (task_id != depends_on_task_id)
);

CREATE INDEX idx_task_dependencies_task ON task_dependencies(task_id);
CREATE INDEX idx_task_dependencies_depends ON task_dependencies(depends_on_task_id);

-- ============================================================
-- RETRIES
-- ============================================================

CREATE TABLE retries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL,
    reason TEXT NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    output JSONB DEFAULT '{}',
    error_log TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_retries_task_id ON retries(task_id);
CREATE INDEX idx_retries_attempt_number ON retries(attempt_number);

-- ============================================================
-- AUDIT LOGS
-- ============================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    actor VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50) NOT NULL DEFAULT 'agent',
    input JSONB DEFAULT '{}',
    output JSONB DEFAULT '{}',
    result audit_result NOT NULL,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_task_id ON audit_logs(task_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_result ON audit_logs(result);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- ============================================================
-- MENTOR INSTRUCTIONS
-- ============================================================

CREATE TABLE mentor_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    instruction_type instruction_type NOT NULL,
    content TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    applied BOOLEAN NOT NULL DEFAULT FALSE,
    embedding vector,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_mentor_instructions_task_id ON mentor_instructions(task_id);
CREATE INDEX idx_mentor_instructions_type ON mentor_instructions(instruction_type);
CREATE INDEX idx_mentor_instructions_applied ON mentor_instructions(applied);
CREATE INDEX idx_mentor_instructions_embedding ON mentor_instructions USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- MENTOR QUOTA
-- ============================================================

CREATE TABLE mentor_quota (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    calls_used INT NOT NULL DEFAULT 0,
    calls_limit INT NOT NULL DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- ============================================================
-- DECISIONS
-- ============================================================

CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    alternatives JSONB DEFAULT '[]',
    decided_by VARCHAR(100) NOT NULL DEFAULT 'mentor',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decisions_project_id ON decisions(project_id);
CREATE INDEX idx_decisions_task_id ON decisions(task_id);

-- ============================================================
-- WORKFLOWS
-- ============================================================

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    current_node VARCHAR(100),
    graph JSONB DEFAULT '{}',
    state JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error TEXT
);

CREATE INDEX idx_workflows_project_id ON workflows(project_id);
CREATE INDEX idx_workflows_status ON workflows(status);

-- ============================================================
-- DEPLOYMENTS
-- ============================================================

CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    environment deployment_env NOT NULL DEFAULT 'staging',
    image_tag VARCHAR(255) NOT NULL,
    status deployment_status NOT NULL DEFAULT 'pending',
    url VARCHAR(500),
    logs TEXT,
    deployed_by VARCHAR(100),
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_deployments_task_id ON deployments(task_id);
CREATE INDEX idx_deployments_environment ON deployments(environment);
CREATE INDEX idx_deployments_status ON deployments(status);

-- ============================================================
-- COST TRACKING (enhanced with LLM call details)
-- ============================================================

CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    cost_usd FLOAT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    status llm_call_status NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cost_tracking_task_id ON cost_tracking(task_id);
CREATE INDEX idx_cost_tracking_project_id ON cost_tracking(project_id);
CREATE INDEX idx_cost_tracking_model ON cost_tracking(model);
CREATE INDEX idx_cost_tracking_agent ON cost_tracking(agent_name);
CREATE INDEX idx_cost_tracking_created_at ON cost_tracking(created_at);
CREATE INDEX idx_cost_tracking_status ON cost_tracking(status);

-- ============================================================
-- LLM CALL LOGS (detailed tracking per LLM call)
-- ============================================================

CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    cost_tracking_id UUID REFERENCES cost_tracking(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    prompt_hash VARCHAR(64),
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    status llm_call_status NOT NULL DEFAULT 'completed',
    error_message TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    circuit_breaker_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_llm_call_logs_task_id ON llm_call_logs(task_id);
CREATE INDEX idx_llm_call_logs_agent ON llm_call_logs(agent_name);
CREATE INDEX idx_llm_call_logs_model ON llm_call_logs(model);
CREATE INDEX idx_llm_call_logs_created_at ON llm_call_logs(created_at);
CREATE INDEX idx_llm_call_logs_status ON llm_call_logs(status);

-- ============================================================
-- EMBEDDING CONFIG (configurable vector dimensions)
-- ============================================================

CREATE TABLE embedding_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(100) NOT NULL,
    dimensions INT NOT NULL DEFAULT 1536,
    cost_per_1k_input_tokens FLOAT NOT NULL DEFAULT 0,
    cost_per_1k_output_tokens FLOAT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed default embedding models
INSERT INTO embedding_config (model_name, provider, dimensions, cost_per_1k_input_tokens) VALUES
    ('text-embedding-3-small', 'openai', 1536, 0.00002),
    ('bge-large-en-v1.5', 'bge', 1024, 0),
    ('bge-m3', 'bge', 1024, 0);

-- ============================================================
-- CIRCUIT BREAKER STATE
-- ============================================================

CREATE TABLE circuit_breaker_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model VARCHAR(100) NOT NULL UNIQUE,
    state VARCHAR(20) NOT NULL DEFAULT 'closed',
    failure_count INT NOT NULL DEFAULT 0,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    half_open_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- NOTIFICATIONS (Human-in-the-loop for BLOCKED tasks)
-- ============================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    channels JSONB DEFAULT '["dashboard"]',
    metadata JSONB DEFAULT '{}',
    sent BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_task_id ON notifications(task_id);
CREATE INDEX idx_notifications_project_id ON notifications(project_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_sent ON notifications(sent);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- ============================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_modules_updated_at BEFORE UPDATE ON modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_mentor_instructions_updated_at BEFORE UPDATE ON mentor_instructions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_circuit_breaker_updated_at BEFORE UPDATE ON circuit_breaker_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================

-- Task summary view (common query optimization)
CREATE VIEW v_task_summary AS
SELECT
    t.id,
    t.title,
    t.status,
    t.priority,
    t.confidence,
    t.risk_level,
    t.retries,
    t.owner,
    p.name AS project_name,
    m.name AS module_name,
    t.created_at,
    t.updated_at,
    t.completed_at,
    t.failed_at,
    t.cancelled_at,
    (SELECT COUNT(*) FROM task_dependencies WHERE task_id = t.id) AS dependency_count,
    (SELECT COUNT(*) FROM retries WHERE task_id = t.id) AS retry_count,
    (SELECT COUNT(*) FROM audit_logs WHERE task_id = t.id) AS audit_count
FROM tasks t
LEFT JOIN projects p ON t.project_id = p.id
LEFT JOIN modules m ON t.module_id = m.id;

-- Cost summary view
CREATE VIEW v_cost_summary AS
SELECT
    ct.project_id,
    ct.agent_name,
    ct.model,
    COUNT(*) AS total_calls,
    SUM(ct.input_tokens) AS total_input_tokens,
    SUM(ct.output_tokens) AS total_output_tokens,
    SUM(ct.cost_usd) AS total_cost_usd,
    AVG(ct.latency_ms) AS avg_latency_ms,
    SUM(CASE WHEN ct.status = 'failed' THEN 1 ELSE 0 END) AS failed_calls,
    SUM(CASE WHEN ct.status = 'timeout' THEN 1 ELSE 0 END) AS timeout_calls
FROM cost_tracking ct
GROUP BY ct.project_id, ct.agent_name, ct.model;

-- ============================================================
-- METADATA
-- ============================================================

-- Version: 2.0.0
-- Created: 2026-05-14
-- Updated: 2026-05-14
-- Changes:
--   - Added FAILED, CANCELLED task statuses
--   - Added users and api_keys tables (auth)
--   - Replaced UUID[] dependencies with junction tables
--   - Added task_outputs table (separate from tasks)
--   - Added mentor_quota table (enforcement)
--   - Added llm_call_logs table (detailed tracking)
--   - Added circuit_breaker_state table
--   - Added embedding_config table (configurable dimensions)
--   - Added deployment_env and deployment_status enums
--   - Added llm_call_status enum
--   - Added cancellation_reason, failure_reason columns to tasks
--   - Added failed_at, cancelled_at columns to tasks
--   - Added task_dependencies.module_dependencies junction tables
--   - Added actor_type to audit_logs
--   - Added decided_by to decisions
--   - Added approved_by (FK to users) to deployments
--   - Enhanced cost_tracking with latency_ms, status, agent_name
--   - Added v_task_summary and v_cost_summary views