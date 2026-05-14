# Data Flow - AI SDLC System

## Tài liệu Luồng Dữ liệu

---

## 1. Tổng quan

Tài liệu này mô tả luồng dữ liệu trong AI SDLC System sử dụng Mermaid diagrams. Mỗi diagram thể hiện một khía cạnh khác nhau của hệ thống: user request, agent coordination, state transition, LLM call, verification, và memory retrieval.

### 1.1 Data Stores Tổng quan

```mermaid
erDiagram
    projects ||--o{ module_specs : contains
    projects ||--o{ tasks : contains
    projects ||--o{ cost_tracking : tracks
    projects ||--o{ project_members : has
    module_specs ||--o{ tasks : contains
    tasks ||--o{ state_transitions : records
    tasks ||--o{ retry_records : tracks
    tasks ||--o{ llm_call_logs : incurs
    users ||--o{ api_keys : owns
    users ||--o{ project_members : belongs_to
    tasks ||--o{ audit_logs : audited_by
    llm_call_logs ||--o{ cost_tracking : aggregates_into
    projects ||--o{ cost_tracking : tracked_in
    tasks ||--o{ cost_tracking : tracked_in

    projects {
        uuid id PK
        string name
        text description
        jsonb tech_stack
        string status
        timestamp created_at
        timestamp updated_at
    }

    module_specs {
        uuid id PK
        uuid project_id FK
        string name
        text description
        jsonb tech_stack
        string status
        timestamp created_at
        timestamp updated_at
    }

    tasks {
        uuid id PK
        uuid module_id FK
        string title
        text description
        string state
        string priority
        integer complexity_score
        string assigned_agent
        integer retry_count
        integer max_retries
        jsonb depends_on
        timestamp created_at
        timestamp updated_at
    }

    state_transitions {
        uuid id PK
        uuid task_id FK
        string from_state
        string to_state
        text reason
        string actor
        jsonb metadata
        timestamp created_at
    }

    audit_logs {
        uuid id PK
        string entity_type
        uuid entity_id
        string action
        string actor
        string actor_type
        jsonb details
        string prev_hash
        string entry_hash
        timestamp created_at
    }

    retry_records {
        uuid id PK
        uuid task_id FK
        integer attempt
        string result
        text error_message
        timestamp created_at
    }

    llm_call_logs {
        uuid id PK
        uuid task_id FK
        uuid project_id FK
        string agent_type
        string model
        string provider
        integer input_tokens
        integer output_tokens
        decimal cost_usd
        integer latency_ms
        string status
        text error_message
        boolean fallback_used
        string fallback_model
        string prompt_hash
        timestamp created_at
    }

    cost_tracking {
        uuid id PK
        uuid project_id FK
        uuid task_id FK
        date date
        string model
        string agent_type
        integer total_calls
        integer total_input_tokens
        integer total_output_tokens
        decimal total_cost_usd
        integer avg_latency_ms
        integer error_count
        integer fallback_count
        timestamp created_at
        timestamp updated_at
    }

    users {
        uuid id PK
        string username
        string email
        string hashed_password
        string full_name
        string role
        boolean is_active
        timestamp last_login
        timestamp created_at
        timestamp updated_at
    }

    api_keys {
        uuid id PK
        uuid user_id FK
        string name
        string key_hash
        string key_prefix
        jsonb permissions
        timestamp expires_at
        timestamp last_used_at
        boolean is_active
        timestamp created_at
    }

    project_members {
        uuid id PK
        uuid project_id FK
        uuid user_id FK
        string role
        timestamp created_at
    }
```

---

## 2. User Request Flow

```mermaid
sequenceDiagram
    actor User
    participant API as API Server
    participant Auth as Auth Service
    participant SM as State Machine
    participant DB as Database
    participant Audit as Audit Logger
    participant WF as Workflow Engine
    participant Agent as Agent Runtime

    User->>API: POST /api/v1/tasks {title, description, priority}
    API->>Auth: Validate token/API key
    Auth-->>API: Authenticated (user_id, role)

    alt Invalid Auth
        API-->>User: 401 Unauthorized
    end

    alt Insufficient Permissions
        API-->>User: 403 Forbidden
    end

    API->>API: Validate input (Pydantic model)
    alt Invalid Input
        API-->>User: 422 Validation Error
    end

    API->>DB: INSERT INTO tasks (state='NEW')
    DB-->>API: Task created (task_id)

    API->>Audit: Log task creation
    Audit->>DB: INSERT INTO audit_logs

    API-->>User: 201 Created {task_id, state='NEW'}

    User->>API: POST /api/v1/tasks/{id}/transition {new_status='ANALYZING'}
    API->>Auth: Validate token/API key
    Auth-->>API: Authenticated

    API->>SM: Validate transition (NEW → ANALYZING)
    SM->>SM: Check valid transition rules
    SM->>SM: Check retry count
    SM->>SM: Check dependencies

    alt Invalid Transition
        SM-->>API: InvalidTransitionError
        API-->>User: 409 Conflict
    end

    SM-->>API: Transition valid
    API->>DB: UPDATE tasks SET state='ANALYZING'
    API->>DB: INSERT INTO state_transitions
    API->>Audit: Log state transition
    Audit->>DB: INSERT INTO audit_logs (with hash chain)

    API->>WF: Trigger workflow for task
    WF->>Agent: Assign task to Gatekeeper

    API-->>User: 200 OK {task_id, old_status, new_status}
```

---

## 3. Agent Coordination Flow

```mermaid
flowchart TB
    Start([User creates task]) --> NEW[Task: NEW]
    NEW --> GK[Gatekeeper Agent]

    subgraph GATEKEEPER["Gatekeeper Classification"]
        GK --> GK_LLM[LLM Call: DeepSeek V4 Flash]
        GK_LLM --> GK_Result{Complexity Score}
        GK_Result -->|Score 1-3| SIMPLE[Routing: Simple]
        GK_Result -->|Score 4-7| STANDARD[Routing: Standard]
        GK_Result -->|Score 8-10| COMPLEX[Routing: Complex]
        GK_Result -->|Missing Info| BLOCKED1[Task: BLOCKED]
    end

    SIMPLE --> ANALYZING[Task: ANALYZING]
    STANDARD --> ANALYZING
    COMPLEX --> ANALYZING

    ANALYZING --> ORC[Orchestrator Agent]

    subgraph ORCHESTRATOR["Orchestrator Planning"]
        ORC --> ORC_LLM[LLM Call: Qwen 3.6 Plus]
        ORC_LLM --> ORC_Result{Task Breakdown}
        ORC_Result -->|Success| PLAN[Task Breakdown + Dependencies]
        ORC_Result -->|Fail| BLOCKED2[Task: BLOCKED]
    end

    PLAN --> PLANNING[Task: PLANNING]

    PLANNING --> SPEC[Specialist Agent]

    subgraph SPECIALIST["Specialist Implementation"]
        SPEC --> SPEC_CTX[Context Builder]
        SPEC_CTX --> SPEC_LLM[LLM Call: DeepSeek V4 Pro/Flash]
        SPEC_LLM --> SPEC_RESULT{Code Generation}
        SPEC_RESULT -->|Success| IMPL[Task: IMPLEMENTING]
        SPEC_RESULT -->|Missing Info| BLOCKED3[Task: BLOCKED]
        SPEC_RESULT -->|Fatal Error| FAIL1[Task: FAILED]
    end

    IMPL --> VERIFY[Verification Pipeline]

    subgraph VERIFICATION["Verification"]
        VERIFY --> LINT[Lint Check]
        LINT --> TEST[Test Run]
        TEST --> BUILD[Build Check]
        BUILD -->|Pass| REVIEWING[Task: REVIEWING]
        BUILD -->|Fail + Retries Left| IMPL_RETRY[Task: IMPLEMENTING retry]
        BUILD -->|Fail + Max Retries| FAIL2[Task: FAILED]
    end

    REVIEWING --> AUD[Auditor Agent]

    subgraph AUDITOR["Auditor Review"]
        AUD --> AUD_LLM[LLM Call: DeepSeek V4 Pro]
        AUD_LLM --> AUD_Result{Verdict}
        AUD_Result -->|Score >= 80%| DONE1[Task: DONE]
        AUD_Result -->|Score 60-80%| IMPL_RETRY2[Task: IMPLEMENTING revise]
        AUD_Result -->|Critical Violation| ESCALATED[Task: ESCALATED]
    end

    ESCALATED --> MENTOR[Mentor Agent]
    subgraph MENTOR_REVIEW["Mentor Decision"]
        MENTOR --> MENTOR_LLM[LLM Call: Qwen 3.6 Plus]
        MENTOR_LLM --> MENTOR_Result{Final Verdict}
        MENTOR_Result -->|Approved + Verified| DONE2[Task: DONE]
        MENTOR_Result -->|New Plan| PLANNING2[Task: PLANNING]
        MENTOR_Result -->|Rejected| FAIL3[Task: FAILED]
    end

    BLOCKED1 -->|Dependency Resolved| ANALYZING
    BLOCKED2 -->|Info Available| ANALYZING
    BLOCKED3 -->|Info Available| PLANNING
    BLOCKED1 -->|User Cancel| CANCELLED([Task: CANCELLED])
    BLOCKED2 -->|User Cancel| CANCELLED
    BLOCKED3 -->|User Cancel| CANCELLED

    style DONE1 fill:#4CAF50,color:#fff
    style DONE2 fill:#4CAF50,color:#fff
    style FAIL1 fill:#F44336,color:#fff
    style FAIL2 fill:#F44336,color:#fff
    style FAIL3 fill:#F44336,color:#fff
    style CANCELLED fill:#9E9E9E,color:#fff
    style ESCALATED fill:#FF9800,color:#fff
    style BLOCKED1 fill:#FFC107,color:#000
    style BLOCKED2 fill:#FFC107,color:#000
    style BLOCKED3 fill:#FFC107,color:#000
```

---

## 4. State Transition Flow

```mermaid
stateDiagram-v2
    [*] --> NEW

    NEW --> ANALYZING: Gatekeeper classified
    NEW --> BLOCKED: Missing info

    ANALYZING --> PLANNING: Orchestrator planned
    ANALYZING --> BLOCKED: Cannot analyze
    ANALYZING --> CANCELLED: User cancelled

    PLANNING --> IMPLEMENTING: Agent accepted
    PLANNING --> BLOCKED: Dependency blocked
    PLANNING --> CANCELLED: User cancelled

    IMPLEMENTING --> VERIFYING: Code complete
    IMPLEMENTING --> BLOCKED: Missing info
    IMPLEMENTING --> FAILED: Unrecoverable error

    VERIFYING --> REVIEWING: Sandbox passed
    VERIFYING --> IMPLEMENTING: Sandbox failed (retry)
    VERIFYING --> FAILED: Critical verification failure

    REVIEWING --> DONE: Auditor approved
    REVIEWING --> IMPLEMENTING: Auditor revise (retry)
    REVIEWING --> ESCALATED: Auditor escalated
    REVIEWING --> CANCELLED: User cancelled

    ESCALATED --> PLANNING: Mentor takeover
    ESCALATED --> FAILED: Mentor rejected
    ESCALATED --> DONE: Mentor approved\n(verified output only)

    BLOCKED --> PLANNING: Dependency resolved
    BLOCKED --> CANCELLED: User cancelled

    DONE --> [*]
    FAILED --> [*]
    CANCELLED --> [*]

    note right of DONE: Terminal state\nTask completed
    note right of FAILED: Terminal state\nUnrecoverable
    note right of CANCELLED: Terminal state\nUser cancelled
    note right of ESCALATED: Requires Mentor\nor human intervention
    note right of BLOCKED: Waiting for\ndependency or info
```

### 4.1 State Transition Data Flow

```mermaid
flowchart LR
    subgraph INPUT["Transition Input"]
        A[task_id]
        B[from_state]
        C[to_state]
        D[reason]
        E[actor]
        F[metadata]
    end

    subgraph VALIDATION["Validation Layer"]
        G[Check valid transition]
        H[Check retry count]
        I[Check dependencies]
        J[Check terminal state]
    end

    subgraph EXECUTION["Execution Layer"]
        K[Acquire row lock<br/>SELECT FOR UPDATE]
        L[Update task state]
        M[Insert state_transition]
        N[Insert audit_log<br/>with hash chain]
        O[Check cost alerts]
    end

    subgraph OUTPUT["Transition Output"]
        P[Task updated]
        Q[Transition logged]
        R[Audit trail created]
        S[Cost tracked]
        T[Event published]
    end

    INPUT --> VALIDATION
    VALIDATION -->|Valid| EXECUTION
    VALIDATION -->|Invalid| ERR[409 Conflict Error]
    EXECUTION --> OUTPUT

    style INPUT fill:#E3F2FD
    style VALIDATION fill:#FFF3E0
    style EXECUTION fill:#E8F5E9
    style OUTPUT fill:#FCE4EC
    style ERR fill:#FFCDD2
```

---

## 5. LLM Call Flow

```mermaid
sequenceDiagram
    participant Agent
    participant API as FastAPI Brain
    participant CB as Context Builder
    participant PR as Prompt Renderer
    participant MR as Model Router
    participant GW as LLM Gateway
    participant CBb as Circuit Breaker
    participant LLM as Provider API
    participant DB as Database
    participant CT as Cost Tracker

    Agent->>API: Request LLM call<br/>{agent_type, task_id, task_spec}

    API->>CB: Build context<br/>{task_spec, agent_type}
    CB->>DB: Query related modules
    CB->>DB: Query relevant memory
    CB->>DB: Query architectural laws
    CB->>CB: Apply truncation strategy
    CB-->>API: ContextParts[] with token counts

    API->>PR: Render prompt<br/>{template_name, variables}
    PR->>PR: Load template from DB/file
    PR->>PR: Substitute variables
    PR->>PR: Compute prompt hash (SHA-256)
    PR->>PR: Count tokens
    PR-->>API: {rendered_prompt, prompt_hash, token_count}

    API->>MR: Select model & path<br/>{agent_type, needs_tools, token_count}
    MR->>MR: Determine if agent needs tools
    MR->>MR: Look up primary model
    MR->>MR: Get fallback chain
    MR->>MR: Check context limit vs token_count
    alt Token_count > limit
        MR->>MR: Try larger context model
    end
    MR-->>API: {selected_model, fallback_chain, llm_path}

    API->>GW: Execute LLM call<br/>{model, prompt, path}
    GW->>CBb: Check circuit state<br/>{provider, model}

    alt Circuit OPEN
        GW->>GW: Skip primary, try fallback
        GW->>LLM: Call fallback model
    else Circuit CLOSED or HALF-OPEN
        GW->>LLM: Call primary model
    end

    LLM-->>GW: Response {content, tokens, latency}

    alt Success
        GW->>DB: INSERT INTO llm_call_logs
        GW->>CT: Update cost_tracking
        CT->>DB: UPSERT INTO cost_tracking
        CT->>CT: Check cost alerts
        CT-->>GW: Cost tracking updated
        GW-->>API: {response, model_used, tokens, cost}
    else Error/Timeout
        alt Retries remaining
            GW->>GW: Wait (exponential backoff)
            GW->>LLM: Retry same model
        else No retries remaining
            alt Fallback models available
                GW->>LLM: Call fallback model
            else All models failed
                GW->>DB: INSERT INTO llm_call_logs (status='error')
                GW-->>API: Error response
            end
        end
    end

    API-->>Agent: LLM response<br/>{content, model_used, tokens, cost, latency, llm_path}
```

### 5.1 LLM Call Data Stores

```mermaid
flowchart TB
    subgraph INPUT_DATA["Input Data"]
        A1[task_id]
        A2[agent_type]
        A3[task_spec]
        A4[model_preference]
    end

    subgraph CONTEXT_SOURCES["Context Sources"]
        B1[Task description<br/>from tasks table]
        B2[Module specs<br/>from module_specs table]
        B3[Related memory<br/>from mentor_instructions]
        B4[Architectural laws<br/>from config]
        B5[Prompt templates<br/>from prompt_template_versions]
    end

    subgraph PROCESSING["Processing"]
        C1[Context Builder: prioritize & truncate]
        C2[Prompt Renderer: substitute & hash]
        C3[Model Router: select & check limits]
        C4[LLM Gateway: call & track]
    end

    subgraph OUTPUT_DATA["Output Data"]
        D1[llm_call_logs: call details]
        D2[cost_tracking: aggregated costs]
        D3[State transition: update task]
        D4[Audit log: record action]
    end

    INPUT_DATA --> PROCESSING
    CONTEXT_SOURCES --> PROCESSING
    PROCESSING --> OUTPUT_DATA

    style INPUT_DATA fill:#E3F2FD
    style CONTEXT_SOURCES fill:#F3E5F5
    style PROCESSING fill:#FFF3E0
    style OUTPUT_DATA fill:#E8F5E9
```

---

## 6. Verification Flow

```mermaid
flowchart TB
    IMPL_DONE[Specialist: Code Complete] --> GIT_COMMIT[Git Commit Checkpoint]
    GIT_COMMIT --> VERIFY_START[/Verification Pipeline Start/]

    VERIFY_START --> LINT{Lint Check}

    LINT -->|Pass| TEST{Unit Tests}
    LINT -->|Fail| LINT_RETRY{Retry < 2?}

    LINT_RETRY -->|Yes| IMPL_RETRY1[Back to IMPLEMENTING]
    LINT_RETRY -->|No| ESCALATED1[ESCALATED]

    TEST -->|Pass| BUILD{Build Check}
    TEST -->|Fail| TEST_RETRY{Retry < 2?}

    TEST_RETRY -->|Yes| IMPL_RETRY2[Back to IMPLEMENTING]
    TEST_RETRY -->|No| ESCALATED2[ESCALATED]

    BUILD -->|Pass| SECURITY{Security Scan}
    BUILD -->|Fail| BUILD_RETRY{Retry < 2?}

    BUILD_RETRY -->|Yes| IMPL_RETRY3[Back to IMPLEMENTING]
    BUILD_RETRY -->|No| ESCALATED3[ESCALATED]

    SECURITY -->|Pass| REVIEWING[Task: REVIEWING]
    SECURITY -->|Critical| ESCALATED4[ESCALATED]

    REVIEWING --> AUDITOR[Auditor Review]

    IMPL_RETRY1 --> SPEC2[Specialist: Fix Code]
    IMPL_RETRY2 --> SPEC2
    IMPL_RETRY3 --> SPEC2
    SPEC2 --> VERIFY_START2[Re-verify]
    VERIFY_START2 --> LINT

    ESCALATED1 --> MENTOR[Mentor Decision]
    ESCALATED2 --> MENTOR
    ESCALATED3 --> MENTOR
    ESCALATED4 --> MENTOR

    MENTOR -->|Takeover + New Plan| PLANNING[Task: PLANNING]
    MENTOR -->|Reject| FAILED[Task: FAILED]
    MENTOR -->|Approve + Previously Verified| DONE[Task: DONE]

    AUDITOR -->|Approve ≥80%| DONE
    AUDITOR -->|Revise 60-80%| SPEC2
    AUDITOR -->|Escalate <60%| ESCALATED1

    style DONE fill:#4CAF50,color:#fff
    style FAILED fill:#F44336,color:#fff
    style ESCALATED1 fill:#FF9800,color:#fff
    style ESCALATED2 fill:#FF9800,color:#fff
    style ESCALATED3 fill:#FF9800,color:#fff
    style ESCALATED4 fill:#FF9800,color:#fff
    style REVIEWING fill:#2196F3,color:#fff
```

### 6.1 Verification Data Flow

```mermaid
flowchart LR
    subgraph INPUT["Verification Input"]
        A1[Task ID]
        A2[Module ID]
        A3[Code files]
        A4[Test files]
    end

    subgraph STEPS["Verification Steps"]
        B1[Step 1: Lint<br/>eslint, prettier]
        B2[Step 2: Test<br/>pytest, vitest]
        B3[Step 3: Build<br/>npm run build]
        B4[Step 4: Security<br/>npm audit]
    end

    subgraph RESULTS["Results Storage"]
        C1[state_transitions: VERIFYING → RESULT]
        C2[retry_records: attempt & result]
        C3[audit_logs: verification details]
    end

    INPUT --> STEPS
    STEPS --> RESULTS

    style INPUT fill:#E3F2FD
    style STEPS fill:#FFF3E0
    style RESULTS fill:#E8F5E9
```

---

## 7. Memory Retrieval Flow

```mermaid
sequenceDiagram
    participant Agent as Agent (e.g., Specialist)
    participant OC as OpenCode Orchestrator
    participant CB as Context Builder
    participant ES as Embedding Search Service
    participant DB as PostgreSQL + pgvector
    participant LLM as LLM Provider

    Agent->>OC: Request context for task<br/>{task_id, agent_type}

    OC->>CB: Build context for agent

    CB->>DB: Query task details<br/>SELECT * FROM tasks WHERE id = task_id
    DB-->>CB: Task data

    CB->>DB: Query module spec<br/>SELECT * FROM module_specs WHERE id = module_id
    DB-->>CB: Module spec

    CB->>ES: Search related modules<br/>"{task_description}"
    ES->>ES: Generate query embedding
    ES->>DB: SELECT * FROM module_spec_embeddings<br/>ORDER BY embedding <=> query_embedding<br/>LIMIT 10
    DB-->>ES: Related modules with similarity scores
    ES-->>CB: Related modules (top 5, similarity > 0.7)

    CB->>ES: Search mentor instructions<br/>"{task_description}"
    ES->>DB: SELECT * FROM mentor_instruction_embeddings<br/>ORDER BY embedding <=> query_embedding<br/>LIMIT 10
    DB-->>ES: Related instructions
    ES-->>CB: Relevant mentor instructions (top 5)

    CB->>DB: Query architectural laws<br/>(filtered by task type)
    DB-->>CB: Relevant laws subset

    CB->>CB: Assemble context parts<br/>with priority ordering

    CB->>CB: Calculate total token count

    alt Token count within limit
        CB-->>OC: Full context (no truncation)
    else Token count exceeds limit
        CB->>CB: Apply truncation strategy<br/>Priority: Task > Output > Prompt > Memory > Modules > Laws
        CB-->>OC: Truncated context
    end

    OC->>OC: Render prompt with context
    OC->>LLM: Execute LLM call with context
    LLM-->>OC: Response
    OC-->>Agent: Context + LLM response
```

### 7.1 Memory Data Lifecycle

```mermaid
flowchart TB
    subgraph CREATE["Create"]
        A1[New task created<br/>→ task_embeddings generated]
        A2[New module spec<br/>→ module_spec_embeddings generated]
        A3[New mentor instruction<br/>→ mentor_instruction_embeddings generated]
        A4[New architecture decision<br/>→ stored in decision_history]
    end

    subgraph PROCESS["Process"]
        B1[Embedding generation<br/>→ text-embedding-3-small]
        B2[Vector storage<br/>→ pgvector tables]
        B3[Similarity search<br/>→ cosine similarity > threshold]
        B4[Context assembly<br/>→ priority-based selection]
    end

    subgraph STORE["Store"]
        C1[tasks table<br/>Task metadata]
        C2[module_specs table<br/>Module specifications]
        C3[mentor_instructions table<br/>Teaching content]
        C4[task_embeddings<br/>Task vectors]
        C5[module_spec_embeddings<br/>Module vectors]
        C6[mentor_instruction_embeddings<br/>Instruction vectors]
    end

    subgraph ARCHIVE["Archive"]
        D1[Tasks > 1 year<br/>→ cold storage]
        D2[Embeddings > 1 year<br/>→ re-evaluate relevance]
        D3[Audit logs > 3 years<br/>→ S3 Glacier]
        D4[LLM call logs > 90 days<br/>→ delete (keep cost summary)]
    end

    CREATE --> PROCESS --> STORE
    STORE --> ARCHIVE

    style CREATE fill:#E3F2FD
    style PROCESS fill:#FFF3E0
    style STORE fill:#E8F5E9
    style ARCHIVE fill:#FFCDD2
```

---

## 8. Data Lifecycle

### 8.1 Data Lifecycle Overview

```mermaid
flowchart LR
    subgraph CREATE_PHASE["CREATE"]
        A1[User input<br/>Task creation]
        A2[Agent output<br/>LLM responses]
        A3[System events<br/>State transitions]
        A4[Cost tracking<br/>LLM call logs]
    end

    subgraph PROCESS_PHASE["PROCESS"]
        B1[State machine<br/>Validate transitions]
        B2[Context builder<br/>Build LLM context]
        B3[Prompt renderer<br/>Template substitution]
        B4[Cost calculator<br/>Token → USD]
    end

    subgraph STORE_PHASE["STORE"]
        C1[PostgreSQL<br/>Primary database]
        C2[pgvector<br/>Embeddings]
        C3[Audit logs<br/>Hash chain]
        C4[Cost tracking<br/>Aggregated]
    end

    subgraph ARCHIVE_PHASE["ARCHIVE"]
        D1[Cold storage<br/>Completed tasks >1y]
        D2[S3 Glacier<br/>Audit logs >3y]
        D3[Delete<br/>LLM logs >90d]
        D4[Anonymize<br/>Inactive users]
    end

    CREATE_PHASE --> PROCESS_PHASE --> STORE_PHASE --> ARCHIVE_PHASE
```

### 8.2 Data Retention Details

| Data Type | Hot Storage | Warm Storage | Cold Storage | Delete |
|-----------|------------|-------------|-------------|--------|
| Active tasks | PostgreSQL (real-time) | — | — | — |
| Completed tasks | 1 year | — | S3 Glacier | After 3 years |
| Failed/Cancelled tasks | 90 days | — | — | After 180 days |
| State transitions | Same as task | — | Same as task | Same as task |
| **Audit logs** | **1 year** | — | **S3 Glacier** | **After 6 years** |
| **LLM call logs** | **90 days** | — | — | **After 90 days** |
| **Cost tracking** | **3 years** | — | **S3 Glacier** | **After 7 years** |
| Embeddings | While active | — | — | Re-embed on model change |
| Prompt templates | Indefinite (versioned) | — | — | Never |
| API keys | While active | — | — | 1 year after revocation |
| Revoked tokens | Until expiry | — | — | After expiry |
| Session data | 7 days | — | — | After 7 days |

### 8.3 Data Flow Between Components

```mermaid
flowchart TB
    subgraph CLIENT["Client Layer"]
        U[User / Dashboard]
        A[Agent Process]
    end

    subgraph API["API Layer"]
        AUTH[Auth Service<br/>JWT + API Key]
        RATE[Rate Limiter<br/>Per-role limits]
        VAL[Input Validator<br/>Pydantic models]
        SM[State Machine<br/>Transition engine]
    end

    subgraph SERVICE["Service Layer"]
        WF[Workflow Engine]
        LLM_GW[LLM Gateway<br/>Circuit Breaker]
        CTX[Context Builder]
        PR[Prompt Renderer]
        COST[Cost Tracker]
        AUDIT[Audit Logger]
    end

    subgraph AGENT["Agent Layer"]
        GK[Gatekeeper<br/>DeepSeek V4 Flash]
        ORC[Orchestrator<br/>Qwen 3.6 Plus]
        SPEC[Specialist<br/>DeepSeek V4 Pro]
        AUD_AG[Auditor<br/>Qwen 3.5 Plus]
        MENTOR_AG[Mentor<br/>Qwen 3.6 Plus]
    end

    subgraph DATA["Data Layer"]
        PG[(PostgreSQL<br/>+ pgvector)]
        REDIS[(Redis<br/>Cache + Rate Limit)]
        FILES[File System<br/>Prompt Templates]
    end

    subgraph EXT["External Providers"]
        LLM1[DeepSeek API]
        LLM2[Qwen API]
        LLM3[OpenAI API<br/>Embeddings]
        OC[OpenCode<br/>LLM + Tools]
    end

    CLIENT --> API
    API --> SERVICE
    SERVICE --> AGENT
    AGENT --> LLM_GW
    LLM_GW -->|Path 1: LiteLLM| LLM1
    LLM_GW -->|Path 1: LiteLLM| LLM2
    LLM_GW -->|Path 2: OpenCode| OC
    SERVICE --> DATA
    API --> DATA

    U -->|HTTP/REST| AUTH
    A -->|API Key| AUTH
    AUTH --> RATE --> VAL --> SM

    SM --> WF --> AGENT
    AGENT --> LLM_GW --> EXT
    LLM_GW --> COST
    LLM_GW --> AUDIT

    CTX --> PG
    PR --> FILES
    COST --> PG
    AUDIT --> PG

    RATE --> REDIS

    style CLIENT fill:#E3F2FD
    style API fill:#FFF3E0
    style SERVICE fill:#E8F5E9
    style AGENT fill:#F3E5F5
    style DATA fill:#FFCDD2
    style EXT fill:#CFD8DC
```

---

## 9. Integration Touchpoints

### 9.1 Component Integration Matrix

| Component | Integrates With | Protocol | Data Exchanged | Failure Mode |
|-----------|----------------|----------|----------------|-------------|
| API Server | Auth Service | Internal function call | JWT validation, API key lookup | 401 Unauthorized |
| API Server | State Machine | Internal function call | Task state transitions | 409 Conflict |
| State Machine | Database | PostgreSQL connection | Task state, audit logs | 500 Database error |
| State Machine | Audit Logger | Internal function call | Transition events | Log failure (non-blocking) |
| Workflow Engine | LLM Gateway | Internal function call | LLM requests/responses | Fallback to next model |
| LLM Gateway | DeepSeek API | HTTPS REST (via LiteLLM) | Prompts, completions, tokens | Circuit breaker → fallback |
| LLM Gateway | Qwen API | HTTPS REST (via LiteLLM) | Prompts, completions, tokens | Circuit breaker → fallback |
| LLM Gateway | OpenAI API | HTTPS REST | Embedding requests | Error + cached embedding |
| LLM Gateway | OpenCode | Process/API calls | LLM calls + tool execution | Graceful degradation to ESCALATED |
| Context Builder | PostgreSQL | SQL queries | Tasks, modules, memory | Use cached context |
| Context Builder | pgvector | Vector similarity search | Related modules, instructions | Fall back to LIKE search |
| Prompt Renderer | File System | File I/O | Prompt templates | Use DB version |
| Prompt Renderer | PostgreSQL | SQL queries | Template overrides | Use file version |
| Cost Tracker | PostgreSQL | SQL queries | LLM call logs, aggregated costs | Log error, continue |
| Rate Limiter | Redis | Redis protocol | Rate limit counters | Allow request (fail open) |

### 9.2 Data Flow Summary per Endpoint

| Endpoint | Source Data | Processing | Destination Data | External Calls |
|----------|------------|-----------|-----------------|----------------|
| `POST /login` | User credentials → Auth Service | Validate, generate JWT | tokens table (refresh) | None |
| `POST /tasks` | Task data → State Machine | Validate, set state=NEW | tasks, audit_logs | None |
| `POST /tasks/{id}/transition` | Transition request → State Machine | Validate, execute transition | tasks, state_transitions, audit_logs | None (unless triggers workflow) |
| `POST /tasks/{id}/transition` (ANALYZING) | Transition → Workflow Engine | Assign to Gatekeeper | tasks (status update) | LLM call (DeepSeek V4 Flash) |
| `POST /tasks/{id}/transition` (IMPLEMENTING→VERIFYING) | Transition → Verification Pipeline | Run lint, test, build | retry_records, audit_logs | OpenCode bash commands |
| `GET /cost-stats` | cost_tracking table | Aggregate by model/agent | Response JSON | None |
| `GET /audit-logs` | audit_logs table | Filter, paginate | Response JSON | None |
| `GET /health` | Database, Redis checks | Health checks | Response JSON | LLM provider ping |

### 9.3 Asynchronous Data Flows

```mermaid
flowchart TB
    subgraph SCHEDULED["Scheduled Jobs"]
        A1[Daily 3AM UTC<br/>Cleanup job<br/>- Delete expired tokens<br/>- Delete old LLM logs<br/>- Archive old audit logs<br/>- Anonymize inactive users]
        A2[Daily 6AM UTC<br/>Cost aggregation<br/>- Aggregate llm_call_logs<br/>- Update cost_tracking<br/>- Check cost alerts]
        A3[Weekly Monday 9AM<br/>Weekly cost report<br/>- Generate report<br/>- Send email]
        A4[Hourly<br/>Stuck task detection<br/>- Find tasks stuck >30min<br/>- Alert team]
        A5[Every 5 min<br/>Circuit breaker health<br/>- Check provider status<br/>- Update metrics]
    end

    subgraph EVENT["Event-Driven"]
        B1[State transition event<br/>→ Trigger workflow]
        B2[LLM call complete<br/>→ Update cost_tracking]
        B3[Cost threshold exceeded<br/>→ Send alert]
        B4[Task completed<br/>→ Notify user]
        B5[Circuit breaker open<br/>→ Alert + switch fallback]
    end

    A1 --> |Writes| PG[(PostgreSQL)]
    A2 --> |Reads + Writes| PG
    A3 --> |Reads| PG
    A3 --> |Sends| EMAIL[(Email)]
    A4 --> |Reads| PG
    A4 --> |Sends| SLACK[(Slack)]
    A5 --> |Reads| REDIS[(Redis)]
    A5 --> |Writes| METRICS[(Prometheus)]

    B1 --> |Triggers| WF[(Workflow Engine)]
    B2 --> |Writes| PG
    B3 --> |Sends| SLACK
    B4 --> |Sends| EMAIL
    B5 --> |Writes| METRICS

    style SCHEDULED fill:#E3F2FD
    style EVENT fill:#FFF3E0
    style PG fill:#E8F5E9
    style REDIS fill:#FFCDD2
    style METRICS fill:#F3E5F5
    style EMAIL fill:#CFD8DC
    style SLACK fill:#CFD8DC
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*