# LLM Observability - AI SDLC System

## Tài liệu Giám sát và Quan sát LLM

---

## 1. Tổng quan

LLM Observability đảm bảo hệ thống AI SDLC có khả năng giám sát, đo lường, và phân tích mọi khía cạnh của LLM calls — từ latency, tokens, cost, đến success rate. Tài liệu này định nghĩa metrics, dashboards, alerting rules, và integration với Prometheus.

### 1.1 Mục tiêu

- **Visibility**: Hiểu rõ mọi LLM call xảy ra trong hệ thống
- **Cost control**: Theo dõi chi phí real-time, phát hiện cost spikes
- **Performance**: Phát hiện latency degradation, error rate tăng
- **Reliability**: Đảm bảo circuit breaker hoạt động đúng, fallback diễn ra như mong đợi
- **Accountability**: Trace mọi decision về model routing, cost, và quality

---

## 2. LLM Call Metrics

### 2.1 Core Metrics per Call

Mỗi LLM call log các thông tin sau vào `llm_call_logs` table:

| Metric | Unit | Source | Ghi chú |
|--------|------|--------|---------|
| `latency_ms` | ms | LLM Gateway | Thời gian từ gửi request đến nhận response |
| `input_tokens` | tokens | Provider response | Token đầu vào gửi đến model |
| `output_tokens` | tokens | Provider response | Token đầu ra từ model |
| `cost_usd` | USD | Calculated | Chi phí tính từ pricing table |
| `status` | enum | LLM Gateway | `success`, `error`, `timeout`, `fallback` |
| `model` | string | Model Router | Model thực tế được gọi |
| `provider` | string | Config | Provider (DeepSeek, Qwen) |
| `agent_type` | string | Caller | Agent nào gọi (gatekeeper, specialist, v.v.) |
| `task_id` | UUID | Caller | Task liên quan |
| `project_id` | UUID | Derived | Project liên quan (qua task) |
| `fallback_used` | boolean | LLM Gateway | Có dùng fallback model không |
| `fallback_model` | string | LLM Gateway | Model fallback nếu có |
| `error_message` | text | Provider | Chi tiết lỗi nếu có |
| `prompt_hash` | string | Prompt Renderer | SHA-256 hash của prompt template |

### 2.2 Aggregated Metrics

Aggregated metrics được tính từ `llm_call_logs` và lưu vào `cost_tracking` table:

```sql
-- cost_tracking aggregation (run periodically)
SELECT
    project_id,
    task_id,
    date(created_at) AS date,
    model,
    COUNT(*) AS total_calls,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(cost_usd) AS total_cost_usd,
    AVG(latency_ms) AS avg_latency_ms,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count,
    SUM(CASE WHEN fallback_used = TRUE THEN 1 ELSE 0 END) AS fallback_count
FROM llm_call_logs
GROUP BY project_id, task_id, date(created_at), model;
```

### 2.3 Per-Model Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `llm_calls_total{model}` | Tổng số calls per model | `COUNT(*) WHERE model = ?` |
| `llm_call_success_rate{model}` | Tỉ lệ thành công | `COUNT(success) / COUNT(*)` |
| `llm_latency_p50{model}` | Latency trung vị | Percentile 50 |
| `llm_latency_p95{model}` | Latency p95 | Percentile 95 |
| `llm_latency_p99{model}` | Latency p99 | Percentile 99 |
| `llm_tokens_input_total{model}` | Tổng input tokens | `SUM(input_tokens)` |
| `llm_tokens_output_total{model}` | Tổng output tokens | `SUM(output_tokens)` |
| `llm_cost_total{model}` | Tổng chi phí | `SUM(cost_usd)` |
| `llm_error_rate{model}` | Tỉ lệ lỗi | `COUNT(error) / COUNT(*)` |
| `llm_fallback_rate{model}` | Tỉ lệ fallback | `COUNT(fallback) / COUNT(*)` |

**Model Performance Targets:**

| Model | Success Rate Target | p50 Latency | p95 Latency | Max Latency |
|-------|--------------------|-----|-----|-----|
| DeepSeek V4 Flash | > 98% | 1s | 3s | 15s |
| DeepSeek V4 Pro | > 97% | 5s | 15s | 60s |
| Qwen 3.5 Plus | > 97% | 4s | 12s | 45s |
| Qwen 3.6 Plus | > 96% | 8s | 25s | 90s |

### 2.4 Per-Agent Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `llm_calls_total{agent_type}` | Tổng calls per agent | `COUNT(*) WHERE agent_type = ?` |
| `llm_cost_total{agent_type}` | Chi phí per agent | `SUM(cost_usd) WHERE agent_type = ?` |
| `llm_avg_latency{agent_type}` | Latency trung bình per agent | `AVG(latency_ms) WHERE agent_type = ?` |
| `llm_tokens_total{agent_type}` | Tổng tokens per agent | `SUM(input_tokens + output_tokens) WHERE agent_type = ?` |

**Agent Budget Targets:**

| Agent | Max Calls/Task | Max Tokens/Task | Max Cost/Task (USD) | Max Latency/Task |
|-------|---------------|-----------------|---------------------|------------------|
| Gatekeeper | 5 | 10,000 | $0.05 | 15s |
| Orchestrator | 20 | 200,000 | $1.00 | 120s |
| Specialist | 50 | 500,000 | $3.00 | 300s |
| Auditor | 30 | 100,000 | $0.50 | 180s |
| Mentor | 10 | 50,000 | $0.50 | 60s |
| DevOps | 20 | 100,000 | $1.00 | 180s |
| Monitoring | 10 | 20,000 | $0.10 | 30s |

---

## 3. Dashboards

### 3.1 LLM Cost Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM COST DASHBOARD                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐│
│  │ Total Cost Today  │  │ Total Cost Week   │  │ Total Cost Month ││
│  │    $23.45         │  │    $127.80        │  │    $456.30       ││
│  │  ▲ 15% vs yest   │  │  ▲ 8% vs last wk  │  │                  ││
│  └───────────────────┘  └───────────────────┘  └──────────────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Daily Cost Trend (30 days)                                  │  │
│  │  $50 ┤                                           ╭──╮        │  │
│  │  $40 ┤                                    ╭──╮   │  │        │  │
│  │  $30 ┤                          ╭──╮   ╭──│  │   │  │        │  │
│  │  $20 ┤              ╭──╮  ╭──╮  │  │   │  │  │   │  │        │  │
│  │  $10 ┤  ╭──╮  ╭──╮  │  │  │  │  │  │   │  │  │   │  │        │  │
│  │   $0 ┼──╯  ╰──╯  ╰──╯  ╰──╯  ╰──╯  ╰───╯  ╰───╯  ╰──╯        │  │
│  │       05/01  05/05  05/09  05/13  05/17  05/21  05/25  05/30  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────┐  ┌──────────────────────┐│
│  │ Cost by Model (This Month)            │  │ Cost by Agent        ││
│  │                                      │  │                      ││
│  │ ┌─ DeepSeek V4 Pro ─── $180.50 ──┐  │  │ ┌─ Specialist ── $120││
│  │ │███████████████████████          │  │  │ │████████████        ││
│  │ ├─ Qwen 3.6 Plus ──── $165.20 ──┤  │  │ ├─ Orchestrator─ $85 ││
│  │ │█████████████████████            │  │  │ │██████████          ││
│  │ ├─ Qwen 3.5 Plus ──── $72.60 ───┤  │  │ ├─ Auditor ────── $60││
│  │ │██████████                       │  │  │ │████████            ││
│  │ └─ DeepSeek V4 Flash ─ $38.00 ───┘  │  │ └─ DevOps ────── $35 ││
│  │    █████                          │  │  │    █████              ││
│  └──────────────────────────────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Latency Distribution Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│                  LLM LATENCY DISTRIBUTION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Latency Histogram (Last 24h)                                │  │
│  │                                                              │  │
│  │  │                                                           │  │
│  │  │     ██                                                    │  │
│  │  │     ██ ██                                                 │  │
│  │  │  ██ ██ ██ ██                                              │  │
│  │  │  ██ ██ ██ ██ ██                                           │  │
│  │  │  ██ ██ ██ ██ ██ ██                                        │  │
│  │  │  ██ ██ ██ ██ ██ ██ ██ ██                                 │  │
│  │  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘  │  │
│  │    0s  1s  2s  3s  5s  7s  10s 15s 20s 30s 45s 60s 90s 120s│  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Latency Percentiles by Model                                │  │
│  │                                                              │  │
│  │  Model               p50    p90    p95    p99    Max          │  │
│  │  ─────────────────────────────────────────────────────       │  │
│  │  DeepSeek V4 Flash   0.8s   2.1s   3.0s   5.2s   12s       │  │
│  │  DeepSeek V4 Pro     4.5s   12s    15s    28s    55s       │  │
│  │  Qwen 3.5 Plus       3.2s   8.5s   12s    18s    42s       │  │
│  │  Qwen 3.6 Plus       7.1s   20s    25s    38s    78s       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────┐  ┌──────────────────┐│
│  │  Slow Calls (>p95) by Agent             │  │ Timeout Trend     ││
│  │                                         │  │                  ││
│  │  Specialist  ████████████  23 calls     │  │ │ ╭───            ││
│  │  Auditor     ████████     15 calls     │  │ ││   ╭──          ││
│  │  Orchestrator ███████      12 calls     │  │ ││   │  ╭──       ││
│  │  DevOps       ████         8 calls      │  │ ││   │  │  ╭     ││
│  │  Mentor       ██           3 calls      │  │ ─┴───┴──┴──┴──   ││
│  └─────────────────────────────────────────┘  └──────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Success Rate Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│                  LLM SUCCESS RATE DASHBOARD                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐│
│  │ Overall Success   │  │ Error Rate Today  │  │ Fallback Rate    ││
│  │    97.3%          │  │    2.7%           │  │    4.1%          ││
│  │  ▲ 0.5% vs last  │  │  ▼ 0.3% vs last  │  │  ▼ 1.2% vs last ││
│  └───────────────────┘  └───────────────────┘  └──────────────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Success Rate by Model (Last 7 days)                         │  │
│  │                                                              │  │
│  │  100%┤                                                       │  │
│  │   99%┤ ──── DeepSeek V4 Flash ────                           │  │
│  │   98%┤ ──── DeepSeek V4 Pro ──────                           │  │
│  │   97%┤          ╭──╮                                         │  │
│  │   96%┤ ──── Qwen 3.5 Plus ────     │  │                     │  │
│  │   95%┤ ──── Qwen 3.6 Plus ──────    │  │                    │  │
│  │      └───┬───┬───┬───┬───┬───┬───┤                         │  │
│  │        Mon  Tue  Wed  Thu  Fri  Sat  Sun                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Error Breakdown (Last 24h)                                  │  │
│  │                                                              │  │
│  │  Error Type          │ Count │ Rate │ Primary Model          │  │
│  │  ────────────────────────────────────────────────────────    │  │
│  │  Timeout             │  23   │ 1.5% │ Qwen 3.6 Plus         │  │
│  │  Rate Limit (429)    │  12   │ 0.8% │ DeepSeek V4 Pro       │  │
│  │  Server Error (5xx)  │   8   │ 0.5% │ Qwen 3.5 Plus        │  │
│  │  Invalid Response    │   5   │ 0.3% │ DeepSeek V4 Flash     │  │
│  │  Context Overflow    │   2   │ 0.1% │ DeepSeek V4 Flash     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 Token Usage Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│                  TOKEN USAGE DASHBOARD                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐│
│  │ Input Tokens Today │  │ Output Tokens Tdy │  │ Total Tokens Tdy ││
│  │   2,450,000        │  │    890,000         │  │   3,340,000      ││
│  └───────────────────┘  └───────────────────┘  └──────────────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Token Usage by Model (This Month)                           │  │
│  │                                                              │  │
│  │  Model             │ Input Token  │ Output Token │ Cost/Month │  │
│  │  ──────────────────────────────────────────────────────────   │  │
│  │  DeepSeek V4 Flash │  1,200,000   │    400,000  │  $15.30    │  │
│  │  DeepSeek V4 Pro   │    800,000   │    300,000  │  $45.20    │  │
│  │  Qwen 3.5 Plus     │    300,000   │    120,000  │  $28.50    │  │
│  │  Qwen 3.6 Plus     │    150,000   │     70,000  │  $38.45    │  │
│  │  ──────────────────────────────────────────────────────────   │  │
│  │  TOTAL             │  2,450,000   │    890,000  │ $127.45    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Input vs Output Ratio by Agent                              │  │
│  │                                                              │  │
│  │  Specialist  ██████████████████████ Input:Output = 3:1       │  │
│  │  Orchestrator████████████████████ Input:Output = 5:1        │  │
│  │  Auditor     ██████████████████     Input:Output = 4:1      │  │
│  │  Mentor      ████████████           Input:Output = 3:1      │  │
│  │  Gatekeeper  ████████                Input:Output = 8:1      │  │
│  │  DevOps      ██████████████          Input:Output = 4:1      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Alerting Rules

### 4.1 Cost Alerts

| Alert | Condition | Severity | Channel | Action |
|-------|-----------|----------|---------|--------|
| Daily Cost Warning | `daily_cost > $5/project` | WARNING | Dashboard | Log only |
| Daily Cost Critical | `daily_cost > $20/project` | CRITICAL | Dashboard + Slack | Log + notify team |
| Daily Cost Blocked | `daily_cost > $50/project` | BLOCKED | Dashboard + Slack + Email | Pause all LLM calls for project |
| Monthly Trend Spike | `7-day cost > 2x previous 7-day` | WARNING | Dashboard | Log + review |
| Cost per Task Anomaly | `cost_per_task > 3x average` | WARNING | Dashboard | Log + flag task |
| Free Tier Risk | `project approaching monthly limit` | WARNING | Dashboard + Email | Notify owner |

**Prometheus Alert Rules:**

```yaml
# cost_alerts.yml
groups:
  - name: llm_cost_alerts
    rules:
      - alert: DailyCostWarning
        expr: sum(ai_sdlc_daily_cost_dollars) by (project_id) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Daily LLM cost warning for project {{ $labels.project_id }}"
          description: "Daily cost (${{ $value }}) exceeds warning threshold ($5)"

      - alert: DailyCostCritical
        expr: sum(ai_sdlc_daily_cost_dollars) by (project_id) > 20
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Daily LLM cost critical for project {{ $labels.project_id }}"
          description: "Daily cost (${{ $value }}) exceeds critical threshold ($20)"

      - alert: DailyCostBlocked
        expr: sum(ai_sdlc_daily_cost_dollars) by (project_id) > 50
        for: 1m
        labels:
          severity: blocked
        annotations:
          summary: "Daily LLM cost exceeded block threshold for project {{ $labels.project_id }}"
          description: "Daily cost (${{ $value }}) exceeds block threshold ($50). Pausing LLM calls."

      - alert: CostTrendSpike
        expr: |
          (sum(ai_sdlc_daily_cost_dollars) offset 7d) * 2 < sum(ai_sdlc_daily_cost_dollars)
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "LLM cost trend spike detected"
          description: "Cost in last 7 days is more than 2x the previous 7 days"
```

### 4.2 Latency Alerts

| Alert | Condition | Severity | Channel | Action |
|-------|-----------|----------|---------|--------|
| High Latency p95 | `llm_latency_p95 > model_target * 2` | WARNING | Dashboard | Log + review |
| Slow LLM Call | `single call latency > 60s` | WARNING | Dashboard | Log |
| LLM Timeout | `single call latency > model_max * 1.5` | CRITICAL | Dashboard + Slack | Trigger fallback |
| Circuit Breaker Open | `circuit_breaker_state == 1` | CRITICAL | Dashboard + Slack | Auto-fallback |
| Circuit Breaker Half-Open | `circuit_breaker_state == 2` | WARNING | Dashboard | Monitor |

**Prometheus Alert Rules:**

```yaml
  - name: llm_latency_alerts
    rules:
      - alert: HighLatencyP95
        expr: |
          histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m]))
          > 2 * histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[1d]))
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "LLM latency p95 is 2x higher than normal"
          description: "Model {{ $labels.model }} latency p95 is {{ $value }}s"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{state="open"} == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.provider }}/{{ $labels.model }}"
          description: "LLM provider {{ $labels.provider }} model {{ $labels.model }} circuit breaker is open. Fallback in effect."
```

### 4.3 Error Rate Alerts

| Alert | Condition | Severity | Channel | Action |
|-------|-----------|----------|---------|--------|
| Error Rate Spike | `error_rate > 10% in 15min` | WARNING | Dashboard | Log + review |
| High Error Rate | `error_rate > 25% in 10min` | CRITICAL | Dashboard + Slack | Auto-fallback |
| Provider Down | `error_rate > 50% in 5min` | CRITICAL | Dashboard + Slack + Email | Circuit breaker open |
| Auth Error | `any auth error (401/403)` | CRITICAL | Slack + Email | Immediate investigation |
| Invalid Response | `invalid_response_rate > 5% in 15min` | WARNING | Dashboard | Log + review prompt |

**Prometheus Alert Rules:**

```yaml
  - name: llm_error_alerts
    rules:
      - alert: LLMErrorRateSpike
        expr: |
          (sum(rate(llm_calls_total{status="error"}[15m]))
          / sum(rate(llm_calls_total[15m]))) > 0.10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM error rate spike detected"
          description: "Error rate is {{ $value | humanizePercentage }} in the last 15 minutes"

      - alert: LLMHighErrorRate
        expr: |
          (sum(rate(llm_calls_total{status="error"}[10m]))
          / sum(rate(llm_calls_total[10m]))) > 0.25
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LLM error rate critically high"
          description: "Error rate is {{ $value | humanizePercentage }} in the last 10 minutes. Fallback models should be active."

      - alert: LLMAuthError
        expr: sum(llm_calls_total{status="auth_error"}) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "LLM authentication error detected"
          description: "An authentication error (401/403) occurred. Check API keys immediately."
```

---

## 5. cost_tracking và llm_call_logs Tables

### 5.1 llm_call_logs Table (Chi tiết mỗi call)

```sql
CREATE TABLE llm_call_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID REFERENCES tasks(id),
    project_id      UUID REFERENCES projects(id),
    agent_type      VARCHAR(50) NOT NULL,          -- 'gatekeeper', 'orchestrator', etc.
    model           VARCHAR(50) NOT NULL,           -- 'deepseek-v4-flash', etc.
    provider        VARCHAR(30) NOT NULL,           -- 'deepseek', 'qwen'
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    cost_usd        DECIMAL(10, 6) NOT NULL,
    latency_ms      INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL,           -- 'success', 'error', 'timeout', 'fallback'
    error_message   TEXT,
    fallback_used   BOOLEAN DEFAULT FALSE,
    fallback_model  VARCHAR(50),
    prompt_hash     VARCHAR(64),                    -- SHA-256 hash of prompt template
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes cho common queries
    CONSTRAINT llm_call_logs_status_check
        CHECK (status IN ('success', 'error', 'timeout', 'fallback'))
);

CREATE INDEX idx_llm_call_logs_task ON llm_call_logs(task_id);
CREATE INDEX idx_llm_call_logs_project ON llm_call_logs(project_id);
CREATE INDEX idx_llm_call_logs_model ON llm_call_logs(model);
CREATE INDEX idx_llm_call_logs_agent ON llm_call_logs(agent_type);
CREATE INDEX idx_llm_call_logs_created ON llm_call_logs(created_at);
CREATE INDEX idx_llm_call_logs_status ON llm_call_logs(status);
CREATE INDEX idx_llm_call_logs_project_date ON llm_call_logs(project_id, created_at);
```

### 5.2 cost_tracking Table (Aggregated Per Day Per Model)

```sql
CREATE TABLE cost_tracking (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id),
    task_id             UUID REFERENCES tasks(id),
    date                DATE NOT NULL,
    model               VARCHAR(50) NOT NULL,
    agent_type          VARCHAR(50),
    total_calls         INTEGER DEFAULT 0,
    total_input_tokens  INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost_usd      DECIMAL(10, 4) DEFAULT 0,
    avg_latency_ms      INTEGER DEFAULT 0,
    max_latency_ms      INTEGER DEFAULT 0,
    p95_latency_ms      INTEGER DEFAULT 0,
    error_count         INTEGER DEFAULT 0,
    fallback_count      INTEGER DEFAULT 0,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE (project_id, task_id, date, model, agent_type)
);

CREATE INDEX idx_cost_tracking_project_date ON cost_tracking(project_id, date);
CREATE INDEX idx_cost_tracking_date ON cost_tracking(date);
CREATE INDEX idx_cost_tracking_model ON cost_tracking(model);
CREATE INDEX idx_cost_tracking_project_model ON cost_tracking(project_id, model);
```

### 5.3 Aggregation Query Pattern

```python
# app/services/cost_tracker.py
from datetime import date, datetime
from sqlalchemy import text

async def aggregate_daily_costs(db: AsyncSession, target_date: date):
    """Aggregate llm_call_logs vào cost_tracking cho một ngày cụ thể."""

    result = await db.execute(text("""
        INSERT INTO cost_tracking (
            project_id, task_id, date, model, agent_type,
            total_calls, total_input_tokens, total_output_tokens,
            total_cost_usd, avg_latency_ms, max_latency_ms,
            p95_latency_ms, error_count, fallback_count
        )
        SELECT
            project_id,
            task_id,
            :target_date AS date,
            model,
            agent_type,
            COUNT(*) AS total_calls,
            SUM(input_tokens) AS total_input_tokens,
            SUM(output_tokens) AS total_output_tokens,
            SUM(cost_usd) AS total_cost_usd,
            AVG(latency_ms)::INTEGER AS avg_latency_ms,
            MAX(latency_ms) AS max_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::INTEGER AS p95_latency_ms,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count,
            SUM(CASE WHEN fallback_used = TRUE THEN 1 ELSE 0 END) AS fallback_count
        FROM llm_call_logs
        WHERE DATE(created_at) = :target_date
        GROUP BY project_id, task_id, model, agent_type
        ON CONFLICT (project_id, task_id, date, model, agent_type)
        DO UPDATE SET
            total_calls = EXCLUDED.total_calls,
            total_input_tokens = EXCLUDED.total_input_tokens,
            total_output_tokens = EXCLUDED.total_output_tokens,
            total_cost_usd = EXCLUDED.total_cost_usd,
            avg_latency_ms = EXCLUDED.avg_latency_ms,
            max_latency_ms = EXCLUDED.max_latency_ms,
            p95_latency_ms = EXCLUDED.p95_latency_ms,
            error_count = EXCLUDED.error_count,
            fallback_count = EXCLUDED.fallback_count,
            updated_at = NOW()
    """), {"target_date": target_date})

    await db.commit()
```

---

## 6. Per-Project Cost Tracking

### 6.1 Project Cost Dashboard API

```python
# GET /api/v1/cost-stats?project_id=uuid
async def get_project_cost_stats(
    project_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "model",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lấy thống kê chi phí cho project."""

    query = text("""
        SELECT
            model,
            agent_type,
            SUM(total_calls) AS total_calls,
            SUM(total_input_tokens) AS total_input_tokens,
            SUM(total_output_tokens) AS total_output_tokens,
            SUM(total_cost_usd) AS total_cost_usd,
            AVG(avg_latency_ms) AS avg_latency_ms,
            SUM(error_count) AS total_errors,
            SUM(fallback_count) AS total_fallbacks
        FROM cost_tracking
        WHERE project_id = :project_id
        AND date BETWEEN :date_from AND :date_to
        GROUP BY model, agent_type
        ORDER BY total_cost_usd DESC
    """)

    result = await db.execute(query, {
        "project_id": project_id,
        "date_from": date_from,
        "date_to": date_to,
    })

    return format_cost_response(result)
```

### 6.2 project_cost_limits Table

```sql
CREATE TABLE project_cost_limits (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID REFERENCES projects(id) UNIQUE NOT NULL,
    daily_limit_usd   DECIMAL(10, 2) DEFAULT 50.00,
    monthly_limit_usd DECIMAL(10, 2) DEFAULT 1000.00,
    warning_threshold  DECIMAL(10, 2) DEFAULT 5.00,
    critical_threshold DECIMAL(10, 2) DEFAULT 20.00,
    blocked_threshold  DECIMAL(10, 2) DEFAULT 50.00,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 6.3 Cost Check Middleware

```python
# app/middleware/cost_check.py

async def check_project_cost_limit(
    project_id: UUID,
    db: AsyncSession,
) -> CostCheckResult:
    """Kiểm tra project cost limit trước khi cho phép LLM call."""

    # Lấy cost limit
    limits = await db.execute(
        text("SELECT * FROM project_cost_limits WHERE project_id = :pid"),
        {"pid": project_id}
    )
    limit_row = limits.first()

    if not limit_row:
        return CostCheckResult(allowed=True, limit_type=None)

    # Tính total cost today
    today_cost = await db.execute(
        text("""
            SELECT COALESCE(SUM(total_cost_usd), 0) as daily_cost
            FROM cost_tracking
            WHERE project_id = :pid AND date = CURRENT_DATE
        """),
        {"pid": project_id}
    )
    daily_cost = today_cost.scalar()

    # Kiểm tra các threshold
    if daily_cost >= limit_row.blocked_threshold:
        return CostCheckResult(
            allowed=False,
            limit_type="blocked",
            message=f"Daily cost ${daily_cost:.2f} exceeds blocked threshold ${limit_row.blocked_threshold}"
        )

    if daily_cost >= limit_row.critical_threshold:
        # Log critical alert
        await log_cost_alert(project_id, "critical", daily_cost, limit_row.critical_threshold)
        return CostCheckResult(allowed=True, limit_type="critical")

    if daily_cost >= limit_row.warning_threshold:
        # Log warning
        await log_cost_alert(project_id, "warning", daily_cost, limit_row.warning_threshold)
        return CostCheckResult(allowed=True, limit_type="warning")

    return CostCheckResult(allowed=True, limit_type=None)
```

---

## 7. Per-Agent Cost Tracking

### 7.1 Agent Cost Report

| Agent | Calls Today | Tokens Today | Cost Today | Avg Latency | Error Rate | Budget Used |
|-------|-------------|-------------|-----------|-------------|-----------|------------|
| Specialist | 45 | 125,000 | $3.20 | 25s | 2.1% | 64% |
| Orchestrator | 22 | 88,000 | $0.85 | 18s | 0.0% | 17% |
| Auditor | 38 | 95,000 | $1.20 | 12s | 1.3% | 40% |
| Gatekeeper | 52 | 15,000 | $0.10 | 1.2s | 0.0% | 2% |
| Mentor | 3 | 18,000 | $0.45 | 28s | 0.0% | 9% |
| DevOps | 8 | 32,000 | $0.35 | 15s | 0.0% | 7% |
| Monitoring | 30 | 8,000 | $0.05 | 0.5s | 0.0% | 1% |

### 7.2 Agent Budget Enforcement

```python
# app/services/agent_budget.py

AGENT_DAILY_BUDGETS = {
    "gatekeeper": {"max_calls": 500, "max_tokens": 100_000, "max_cost_usd": 5.00},
    "orchestrator": {"max_calls": 500, "max_tokens": 1_000_000, "max_cost_usd": 20.00},
    "specialist": {"max_calls": 100, "max_tokens": 5_000_000, "max_cost_usd": 50.00},
    "auditor": {"max_calls": 200, "max_tokens": 2_000_000, "max_cost_usd": 30.00},
    "mentor": {"max_calls": 10, "max_tokens": 500_000, "max_cost_usd": 10.00},
    "devops": {"max_calls": 50, "max_tokens": 1_000_000, "max_cost_usd": 20.00},
    "monitoring": {"max_calls": None, "max_tokens": 200_000, "max_cost_usd": 5.00},
}

async def check_agent_budget(agent_type: str, db: AsyncSession) -> BudgetCheckResult:
    """Kiểm tra agent daily budget."""

    budget = AGENT_DAILY_BUDGETS.get(agent_type)
    if not budget:
        return BudgetCheckResult(allowed=True)

    today_usage = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_calls,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost
            FROM llm_call_logs
            WHERE agent_type = :agent_type
            AND DATE(created_at) = CURRENT_DATE
        """),
        {"agent_type": agent_type}
    )
    usage = today_usage.first()

    if budget["max_calls"] and usage.total_calls >= budget["max_calls"]:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Agent {agent_type}: daily call limit {budget['max_calls']} reached"
        )

    if usage.total_tokens >= budget["max_tokens"]:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Agent {agent_type}: daily token limit {budget['max_tokens']} reached"
        )

    if usage.total_cost >= budget["max_cost_usd"]:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Agent {agent_type}: daily cost limit ${budget['max_cost_usd']:.2f} reached"
        )

    return BudgetCheckResult(allowed=True)
```

---

## 8. Daily/Weekly Cost Reports

### 8.1 Daily Cost Report

```python
# app/reports/daily_cost.py

async def generate_daily_cost_report(db: AsyncSession, target_date: date) -> dict:
    """Tạo báo cáo chi phí hàng ngày."""

    report = {}

    # Tổng chi phí ngày
    daily_total = await db.execute(text("""
        SELECT
            SUM(total_calls) as total_calls,
            SUM(total_input_tokens) as total_input_tokens,
            SUM(total_output_tokens) as total_output_tokens,
            SUM(total_cost_usd) as total_cost_usd,
            AVG(avg_latency_ms) as avg_latency_ms
        FROM cost_tracking
        WHERE date = :target_date
    """), {"target_date": target_date})

    # Per-model breakdown
    model_breakdown = await db.execute(text("""
        SELECT
            model,
            SUM(total_calls) as total_calls,
            SUM(total_input_tokens) as total_input_tokens,
            SUM(total_output_tokens) as total_output_tokens,
            SUM(total_cost_usd) as total_cost_usd,
            AVG(avg_latency_ms) as avg_latency_ms,
            SUM(error_count) as total_errors,
            SUM(fallback_count) as total_fallbacks
        FROM cost_tracking
        WHERE date = :target_date
        GROUP BY model
        ORDER BY total_cost_usd DESC
    """), {"target_date": target_date})

    # Per-agent breakdown
    agent_breakdown = await db.execute(text("""
        SELECT
            agent_type,
            SUM(total_calls) as total_calls,
            SUM(total_input_tokens + total_output_tokens) as total_tokens,
            SUM(total_cost_usd) as total_cost_usd,
            AVG(avg_latency_ms) as avg_latency_ms
        FROM cost_tracking
        WHERE date = :target_date
        GROUP BY agent_type
        ORDER BY total_cost_usd DESC
    """), {"target_date": target_date})

    # Per-project breakdown
    project_breakdown = await db.execute(text("""
        SELECT
            project_id,
            SUM(total_cost_usd) as total_cost_usd
        FROM cost_tracking
        WHERE date = :target_date
        GROUP BY project_id
        ORDER BY total_cost_usd DESC
    """), {"target_date": target_date})

    # Comparison với ngày trước
    prev_day_total = await db.execute(text("""
        SELECT COALESCE(SUM(total_cost_usd), 0)
        FROM cost_tracking
        WHERE date = :prev_date
    """), {"prev_date": target_date - timedelta(days=1)})

    report = {
        "date": target_date.isoformat(),
        "summary": {
            "total_calls": daily_total.total_calls,
            "total_tokens": daily_total.total_input_tokens + daily_total.total_output_tokens,
            "total_cost_usd": float(daily_total.total_cost_usd),
            "avg_latency_ms": float(daily_total.avg_latency_ms),
            "cost_change_vs_yesterday": calculate_change(
                float(daily_total.total_cost_usd),
                float(prev_day_total.scalar() or 0)
            ),
        },
        "by_model": format_rows(model_breakdown),
        "by_agent": format_rows(agent_breakdown),
        "by_project": format_rows(project_breakdown),
        "alerts": await get_cost_alerts(db, target_date),
    }

    return report
```

### 8.2 Weekly Cost Report

```python
async def generate_weekly_cost_report(db: AsyncSession, week_start: date) -> dict:
    """Tạo báo cáo chi phí hàng tuần."""

    week_end = week_start + timedelta(days=6)

    # Weekly totals
    weekly_total = await db.execute(text("""
        SELECT
            SUM(total_calls) as total_calls,
            SUM(total_cost_usd) as total_cost_usd,
            AVG(avg_latency_ms) as avg_latency_ms,
            SUM(error_count) as total_errors,
            SUM(fallback_count) as total_fallbacks
        FROM cost_tracking
        WHERE date BETWEEN :start AND :end
    """), {"start": week_start, "end": week_end})

    # Daily trend
    daily_trend = await db.execute(text("""
        SELECT
            date,
            SUM(total_calls) as total_calls,
            SUM(total_cost_usd) as total_cost_usd
        FROM cost_tracking
        WHERE date BETWEEN :start AND :end
        GROUP BY date
        ORDER BY date
    """), {"start": week_start, "end": week_end})

    # Comparison với tuần trước
    prev_week_total = await db.execute(text("""
        SELECT COALESCE(SUM(total_cost_usd), 0)
        FROM cost_tracking
        WHERE date BETWEEN :start AND :end
    """), {
        "start": week_start - timedelta(days=7),
        "end": week_end - timedelta(days=7),
    })

    # Top 5 projects by cost
    top_projects = await db.execute(text("""
        SELECT
            project_id,
            SUM(total_cost_usd) as total_cost_usd,
            SUM(total_calls) as total_calls
        FROM cost_tracking
        WHERE date BETWEEN :start AND :end
        GROUP BY project_id
        ORDER BY total_cost_usd DESC
        LIMIT 5
    """), {"start": week_start, "end": week_end})

    return {
        "week": f"{week_start.isoformat()} to {week_end.isoformat()}",
        "summary": {
            "total_calls": weekly_total.total_calls,
            "total_cost_usd": float(weekly_total.total_cost_usd),
            "avg_daily_cost": float(weekly_total.total_cost_usd) / 7,
            "error_rate": weekly_total.total_errors / max(weekly_total.total_calls, 1),
            "fallback_rate": weekly_total.total_fallbacks / max(weekly_total.total_calls, 1),
            "cost_change_vs_last_week": calculate_change(
                float(weekly_total.total_cost_usd),
                float(prev_week_total.scalar() or 0)
            ),
        },
        "daily_trend": format_rows(daily_trend),
        "top_projects": format_rows(top_projects),
        "recommendations": generate_recommendations(weekly_total, daily_trend),
    }
```

### 8.3 Cost Report Delivery

| Report | Frequency | Delivery | Format | Recipients |
|--------|-----------|----------|--------|-----------|
| Daily summary | Daily 6AM UTC | Dashboard + Email | HTML/JSON | Project owners, team |
| Weekly deep dive | Monday 9AM UTC | Email | HTML/PDF | Project owners, management |
| Cost alert | Real-time | Dashboard + Slack | JSON | On-call team |
| Monthly budget review | 1st of month | Email + Dashboard | PDF | Management, finance |

---

## 9. Integration với Prometheus Metrics

### 9.1 Prometheus Metrics Registry

```python
# app/metrics/llm_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary

# ---- LLM Call Metrics ----

llm_calls_total = Counter(
    'ai_sdlc_llm_calls_total',
    'Total LLM API calls',
    ['model', 'agent_type', 'provider', 'status']
)

llm_call_duration_seconds = Histogram(
    'ai_sdlc_llm_call_duration_seconds',
    'LLM call duration in seconds',
    ['model', 'agent_type'],
    buckets=[0.5, 1, 2.5, 5, 10, 30, 60, 90, 120]
)

llm_tokens_total = Counter(
    'ai_sdlc_llm_tokens_total',
    'Total tokens used by LLM calls',
    ['model', 'token_type']  # token_type: input, output
)

llm_cost_dollars_total = Counter(
    'ai_sdlc_llm_cost_dollars_total',
    'Total LLM cost in dollars',
    ['model', 'agent_type', 'project_id']
)

llm_fallbacks_total = Counter(
    'ai_sdlc_llm_fallbacks_total',
    'Total LLM fallback model activations',
    ['primary_model', 'fallback_model', 'agent_type']
)

# ---- Circuit Breaker Metrics ----

circuit_breaker_state = Gauge(
    'ai_sdlc_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['provider', 'model']
)

circuit_breaker_failures_total = Counter(
    'ai_sdlc_circuit_breaker_failures_total',
    'Total circuit breaker failure recordings',
    ['provider', 'model']
)

# ---- Cost Metrics ----

daily_cost_dollars = Gauge(
    'ai_sdlc_daily_cost_dollars',
    'Daily LLM cost per project',
    ['project_id']
)

monthly_cost_dollars = Gauge(
    'ai_sdlc_monthly_cost_dollars',
    'Monthly LLM cost per project',
    ['project_id']
)

project_cost_limit_usd = Gauge(
    'ai_sdlc_project_cost_limit_usd',
    'Cost limit per project',
    ['project_id', 'threshold_type']  # threshold_type: warning, critical, blocked
)

# ---- State Machine Metrics ----

state_transitions_total = Counter(
    'ai_sdlc_state_transitions_total',
    'Total state machine transitions',
    ['from_state', 'to_state']
)

active_tasks_gauge = Gauge(
    'ai_sdlc_active_tasks',
    'Active tasks by state',
    ['state']
)

task_duration_seconds = Histogram(
    'ai_sdlc_task_duration_seconds',
    'Task duration from creation to completion',
    ['final_state'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400]
)
```

### 9.2 Metrics Collection Middleware

```python
# app/middleware/metrics.py
import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.metrics.llm_metrics import llm_call_duration_seconds, state_transitions_total

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Record HTTP request metrics
        llm_call_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).observe(duration)

        return response

class LLMMetricsCollector:
    """Collect LLM call metrics và push to Prometheus."""

    async def record_call(self, log: LLMCallLog):
        llm_calls_total.labels(
            model=log.model,
            agent_type=log.agent_type,
            provider=log.provider,
            status=log.status,
        ).inc()

        llm_call_duration_seconds.labels(
            model=log.model,
            agent_type=log.agent_type,
        ).observe(log.latency_ms / 1000)

        llm_tokens_total.labels(
            model=log.model,
            token_type='input',
        ).inc(log.input_tokens)

        llm_tokens_total.labels(
            model=log.model,
            token_type='output',
        ).inc(log.output_tokens)

        llm_cost_dollars_total.labels(
            model=log.model,
            agent_type=log.agent_type,
            project_id=str(log.project_id),
        ).inc(log.cost_usd)

        if log.fallback_used:
            llm_fallbacks_total.labels(
                primary_model=log.model,
                fallback_model=log.fallback_model,
                agent_type=log.agent_type,
            ).inc()

    async def record_transition(self, from_state: str, to_state: str):
        state_transitions_total.labels(
            from_state=from_state,
            to_state=to_state,
        ).inc()

    async def update_active_tasks_gauge(self, db: AsyncSession):
        result = await db.execute(text("""
            SELECT state, COUNT(*) as count
            FROM tasks
            WHERE state NOT IN ('DONE', 'FAILED', 'CANCELLED')
            GROUP BY state
        """))
        for row in result:
            active_tasks_gauge.labels(state=row.state).set(row.count)

    async def update_cost_gauges(self, db: AsyncSession):
        """Update daily và monthly cost gauges."""
        daily = await db.execute(text("""
            SELECT project_id, SUM(total_cost_usd) as cost
            FROM cost_tracking
            WHERE date = CURRENT_DATE
            GROUP BY project_id
        """))
        for row in daily:
            daily_cost_dollars.labels(project_id=str(row.project_id)).set(float(row.cost))

        monthly = await db.execute(text("""
            SELECT project_id, SUM(total_cost_usd) as cost
            FROM cost_tracking
            WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY project_id
        """))
        for row in monthly:
            monthly_cost_dollars.labels(project_id=str(row.project_id)).set(float(row.cost))

    async def update_circuit_breaker_gauges(self):
        """Update circuit breaker state gauges."""
        for (provider, model), cb in circuit_breakers.items():
            state_map = {"closed": 0, "open": 1, "half_open": 2}
            circuit_breaker_state.labels(
                provider=provider,
                model=model,
            ).set(state_map[cb.state])
```

### 9.3 Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "AI SDLC - LLM Observability",
    "panels": [
      {
        "title": "Total Cost (Today)",
        "type": "stat",
        "targets": [{"expr": "sum(ai_sdlc_daily_cost_dollars)"}],
        "fieldConfig": {"unit": "currencyUSD", "thresholds": {"steps": [{"value": 5, "color": "yellow"}, {"value": 20, "color": "orange"}, {"value": 50, "color": "red"}]}}
      },
      {
        "title": "LLM Calls (5m rate)",
        "type": "timeseries",
        "targets": [{"expr": "sum(rate(ai_sdlc_llm_calls_total[5m])) by (model)"}]
      },
      {
        "title": "Latency p95 by Model",
        "type": "timeseries",
        "targets": [{"expr": "histogram_quantile(0.95, sum(rate(ai_sdlc_llm_call_duration_seconds_bucket[5m])) by (le, model))"}]
      },
      {
        "title": "Error Rate by Model",
        "type": "timeseries",
        "targets": [{"expr": "sum(rate(ai_sdlc_llm_calls_total{status=\"error\"}[5m])) / sum(rate(ai_sdlc_llm_calls_total[5m])) by (model)"}]
      },
      {
        "title": "Cost by Model (7d)",
        "type": "barchart",
        "targets": [{"expr": "sum(ai_sdlc_llm_cost_dollars_total) by (model)"}]
      },
      {
        "title": "Circuit Breaker States",
        "type": "stat",
        "targets": [{"expr": "ai_sdlc_circuit_breaker_state"}]
      },
      {
        "title": "Active Tasks by State",
        "type": "barchart",
        "targets": [{"expr": "ai_sdlc_active_tasks"}]
      },
      {
        "title": "Fallback Rate",
        "type": "timeseries",
        "targets": [{"expr": "sum(rate(ai_sdlc_llm_fallbacks_total[5m])) by (primary_model, fallback_model)"}]
      }
    ]
  }
}
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*