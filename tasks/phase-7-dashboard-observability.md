# PHASE 7 — DASHBOARD & OBSERVABILITY (2–3 tuần)

## Mục tiêu
Visibility — quan sát toàn hệ thống, debug workflow dễ, theo dõi cost & reliability.

## Tech Stack
| Thành phần | Tech |
|---|---|
| Frontend | Next.js, TypeScript |
| Styling | TailwindCSS |
| Charts | Recharts |
| State | Zustand |
| Metrics | Prometheus |
| Logs | Loki |
| Visualization | Grafana |
| Tracing | OpenTelemetry |
| Models | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus, MiniMax M2.7 |

---

## 7.1. Frontend Setup

### Mô tả
Setup Next.js project với TailwindCSS, Zustand, Recharts.

### Tasks
- [ ] **7.1.1** — Setup Next.js project
  - `npx create-next-app@latest apps/dashboard --typescript --tailwind --app`
  - Config: TypeScript strict mode, App Router
- [ ] **7.1.2** — Setup TailwindCSS
  - Config tailwind.config.js
  - Tạo global styles
  - Tạo theme variables (colors, spacing, fonts)
- [ ] **7.1.3** — Setup Zustand (state management)
  - Install zustand
  - Tạo stores: taskStore, projectStore, workflowStore, alertStore
- [ ] **7.1.4** — Setup Recharts (charts)
  - Install recharts
  - Tạo chart components base (LineChart, BarChart, PieChart)
- [ ] **7.1.5** — Cấu hình routing
  - Routes: /, /projects, /tasks, /workflow, /agents, /cost, /alerts, /audit, /memory
  - Layout với sidebar navigation
- [ ] **7.1.6** — Tạo layout cơ bản
  - Sidebar với navigation links
  - Header với user info, alerts badge
  - Main content area
  - Responsive design (mobile, tablet, desktop)

### Output
- Next.js app chạy được
- Layout cơ bản
- Routing configured

---

## 7.2. Dashboard Pages

### Mô tả
Tạo các trang dashboard để hiển thị thông tin hệ thống.

### Tasks
- [ ] **7.2.1** — Tạo trang: Project Overview (/)
  - Hiển thị: tổng projects, active projects, completion rate
  - Charts: projects by status, tasks by status
  - Recent activity feed
- [ ] **7.2.2** — Tạo trang: Task List (/tasks)
  - Bảng tasks với columns: title, status, confidence, retry_count, owner, priority
  - Filtering: by status, priority, project
  - Sorting: by date, priority, confidence
  - Pagination
- [ ] **7.2.3** — Tạo trang: Workflow Graph (/workflow)
  - Hiển thị state machine diagram
  - Highlight current state của tasks
  - Animation cho state transitions
- [ ] **7.2.4** — Tạo trang: Agent Status (/agents)
  - Hiển thị: agent đang làm gì, task hiện tại, status
  - Agent activity timeline
  - Agent performance metrics
- [ ] **7.2.5** — Tạo trang: Mentor Calls (/cost)
  - Hiển thị: số mentor calls hôm nay, tuần này, tháng này
  - Cost breakdown by model
  - Mentor quota status
- [ ] **7.2.6** — Tạo trang: Failures & Bottlenecks (/alerts)
  - Hiển thị: tasks fail, retry loops, escalations
  - Alert list với severity
  - Trend chart: failures over time
- [ ] **7.2.7** — Tạo trang: Audit Logs (/audit)
  - Bảng audit logs với columns: action, actor, task, result, timestamp
  - Filtering: by actor, action, result, date range
  - Export to CSV
- [ ] **7.2.8** — Tạo trang: Memory/Instructions (/memory)
  - Hiển thị: instructions, decisions, lessons learned
  - Search functionality
  - Filter by type

### Output
- 8 dashboard pages
- Responsive design
- Data từ API

---

## 7.3. Dashboard Components

### Mô tả
Tạo reusable components cho dashboard.

### Tasks
- [ ] **7.3.1** — Component: TaskCard
  - Hiển thị: title, status badge, confidence gauge, retry counter, priority badge
  - Click để xem chi tiết
  - Props: task object
- [ ] **7.3.2** — Component: WorkflowVisualization
  - Hiển thị state machine diagram
  - Highlight active states
  - Props: workflow_state
- [ ] **7.3.3** — Component: ConfidenceGauge
  - Circular gauge với color coding (green/yellow/red)
  - Props: confidence value (0-1)
- [ ] **7.3.4** — Component: RetryCounter
  - Hiển thị số retries với warning icon nếu gần limit
  - Props: retry_count, max_retries
- [ ] **7.3.5** — Component: CostChart
  - Bar chart: cost by model, by day
  - Props: cost_data
- [ ] **7.3.6** — Component: AgentActivityFeed
  - List: agent actions với timestamp
  - Props: activity_list
- [ ] **7.3.7** — Component: AlertBanner
  - Hiển thị alerts với severity color
  - Dismissible
  - Props: alert object

### Output
- 7 reusable components
- TypeScript types

---

## 7.4. Dashboard API Integration

### Mô tả
Connect dashboard đến backend API, real-time updates.

### Tasks
- [ ] **7.4.1** — Setup API client
  - File: `apps/dashboard/lib/api.ts`
  - Base URL từ env: `NEXT_PUBLIC_API_URL`
  - Axios instance với interceptors
  - Error handling
- [ ] **7.4.2** — Implement real-time updates (WebSocket)
  - Connect WebSocket đến backend
  - Listen for: task status changes, new alerts, agent updates
  - Update UI real-time
  - File: `apps/dashboard/lib/websocket.ts`
- [ ] **7.4.3** — Implement pagination cho task list
  - Server-side pagination
  - Page controls trong UI
- [ ] **7.4.4** — Implement filtering và sorting
  - Filter controls trong UI
  - Send filter params to API
- [ ] **7.4.5** — Implement data fetching hooks
  - Custom React hooks: useTasks, useProjects, useWorkflow
  - SWR hoặc React Query cho caching
- [ ] **7.4.6** — Test dashboard integration
  - Test data loading
  - Test real-time updates
  - Test error handling
  - Test pagination, filtering

### Output
- Dashboard connected to API
- Real-time updates
- Tests pass

---

## 7.5. Monitoring Stack

### Mô tả
Setup Prometheus, Loki, Grafana, OpenTelemetry.

### Tasks
- [ ] **7.5.1** — Setup Prometheus (metrics)
  - Docker compose: prometheus service
  - Config: scrape targets (FastAPI, agents)
  - Prometheus rules
  - File: `docker-compose.monitoring.yml`
- [ ] **7.5.2** — Setup Loki (logs)
  - Docker compose: loki service
  - Config: log retention, storage
  - Promtail for log collection
- [ ] **7.5.3** — Setup Grafana (visualization)
  - Docker compose: grafana service
  - Config: Prometheus datasource, Loki datasource
  - Import dashboards
- [ ] **7.5.4** — Setup OpenTelemetry (tracing)
  - Install OpenTelemetry SDK trong FastAPI
  - Config: exporter (Jaeger/Tempo)
  - Instrument agents
- [ ] **7.5.5** — Cấu hình Grafana dashboards
  - Dashboard: System Overview (tasks, agents, cost)
  - Dashboard: Workflow Performance (latency, success rate)
  - Dashboard: Cost Tracking (token usage, model costs)
  - Dashboard: Error Tracking (errors, retries, escalations)
- [ ] **7.5.6** — Cấu hình alert rules
  - Alert: task fail rate > 10%
  - Alert: mentor quota > 80%
  - Alert: workflow timeout
  - Alert: high error rate
- [ ] **7.5.7** — Test monitoring stack
  - Generate test metrics
  - Verify Grafana dashboards
  - Verify alerts

### Output
- Monitoring stack hoạt động
- Grafana dashboards
- Alert rules
- Tests pass

---

## 7.6. Observability Integration

### Mô tả
Instrument agents và workflow với OpenTelemetry.

### Tasks
- [ ] **7.6.1** — Implement OpenTelemetry instrumentation trong agents
  - Trace: agent execution, model calls, verification
  - Span: mỗi agent action
  - Function: `instrument_agent(agent_name) -> tracer`
- [ ] **7.6.2** — Implement metrics export
  - Metrics: task duration, success rate, cost, retry count
  - Export to Prometheus
  - Function: `export_metrics(name, value, labels) -> status`
- [ ] **7.6.3** — Implement log aggregation
  - Structured logging (JSON)
  - Send logs to Loki
  - Function: `log_event(level, message, context) -> status`
- [ ] **7.6.4** — Implement distributed tracing
  - Trace ID propagate qua workflow nodes
  - Correlate logs với traces
  - Function: `create_trace(context) -> trace_id`
- [ ] **7.6.5** — Test observability end-to-end
  - Chạy workflow
  - Verify traces trong Jaeger/Tempo
  - Verify metrics trong Prometheus
  - Verify logs trong Loki

### Output
- Observability tích hợp hoàn chỉnh
- Traces, metrics, logs
- Tests pass

---

## Checklist Phase 7

| # | Task | Status | Notes |
|---|---|---|---|
| 7.1 | Frontend Setup | ⬜ | Next.js, Tailwind, Zustand, Recharts |
| 7.2 | Dashboard Pages | ⬜ | 8 pages |
| 7.3 | Dashboard Components | ⬜ | 7 reusable components |
| 7.4 | Dashboard API Integration | ⬜ | WebSocket, pagination, filtering |
| 7.5 | Monitoring Stack | ⬜ | Prometheus, Loki, Grafana |
| 7.6 | Observability Integration | ⬜ | OpenTelemetry |

**Definition of Done cho Phase 7:**
- [ ] Dashboard chạy được với 8 pages
- [ ] Real-time updates hoạt động
- [ ] Grafana dashboards hoạt động
- [ ] OpenTelemetry tracing hoạt động
- [ ] Alert rules configured
