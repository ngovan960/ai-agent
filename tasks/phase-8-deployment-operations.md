# PHASE 8 — DEPLOYMENT & OPERATIONS (2–3 tuần)

## Mục tiêu
AI deploy thật — autonomous staging deploy, safe production deploy, rollback automation.

## Tech Stack
| Thành phần | Tech |
|---|---|
| Container Orchestration | Docker Compose / Kubernetes |
| CI/CD | GitHub Actions |
| Reverse Proxy | Nginx |
| Cloud | AWS / Hetzner / GCP |
| Models | DeepSeek V4 Flash/Pro, Qwen 3.5/3.6 Plus, MiniMax M2.7 |

---

## 8.1. Staging Deployment

### Mô tả
AI tự build image, deploy staging, verify staging.

### Tasks
- [ ] **8.1.1** — Implement build image service
  - File: `services/orchestrator/services/deployment_service.py`
  - Function: `build_image(code_path, version) -> image_tag`
  - Input: verified_code
  - Action: docker build với Dockerfile
- [ ] **8.1.2** — Implement deploy staging service
  - Function: `deploy_staging(image_tag) -> deployment_info`
  - Action: push image, deploy to staging environment
  - Output: staging_url, deployment_id
- [ ] **8.1.3** — Implement verify staging service
  - Function: `verify_staging(staging_url) -> result`
  - Action: run health check, smoke tests
- [ ] **8.1.4** — Build API: POST /api/v1/deploy/staging
  - Input: { "task_id": "...", "image_tag": "..." }
  - Action: build → deploy → verify
  - Output: deployment_info + verification_result
- [ ] **8.1.5** — Build API: GET /api/v1/deploy/staging/{deployment_id}
  - Output: deployment status, logs, verification result
- [ ] **8.1.6** — Implement staging environment config
  - File: `services/orchestrator/config/staging_config.yaml`
  - Config: environment variables, resource limits, replicas
- [ ] **8.1.7** — Implement deployment audit logging
  - Log: who deployed, when, what image, result
  - Function: `log_deployment(deployment_info) -> audit_entry`
- [ ] **8.1.8** — Unit test cho staging deployment
  - Test build image
  - Test deploy staging
  - Test verify staging
  - Test audit logging

### Output
- Staging deployment hoạt động
- API deployment
- Tests pass

---

## 8.2. Production Approval

### Mô tả
Critical tasks cần human approval trước khi deploy production.

### Tasks
- [ ] **8.2.1** — Implement approval workflow service
  - File: `services/orchestrator/services/approval_service.py`
  - Rule: risk = CRITICAL → require human approval
  - Function: `require_approval(deployment) -> approval_request`
- [ ] **8.2.2** — Implement approval UI trong dashboard
  - Page: /approvals
  - Hiển thị: pending approvals với details
  - Actions: approve, reject, request changes
- [ ] **8.2.3** — Build API: POST /api/v1/deploy/production/request
  - Input: { "deployment_id": "...", "reason": "..." }
  - Output: approval_request
- [ ] **8.2.4** — Build API: POST /api/v1/deploy/production/approve
  - Input: { "approval_id": "...", "approver": "..." }
  - Output: approval_result
- [ ] **8.2.5** — Build API: POST /api/v1/deploy/production/reject
  - Input: { "approval_id": "...", "reason": "..." }
  - Output: rejection_result
- [ ] **8.2.6** — Implement approval timeout handling
  - Timeout: 24 hours (configurable)
  - Nếu timeout → auto-reject hoặc escalate
- [ ] **8.2.7** — Implement approval notification
  - Notify user khi có approval request
  - Notify khi approved/rejected
- [ ] **8.2.8** — Unit test cho production approval
  - Test approval workflow
  - Test approval API
  - Test timeout handling
  - Test notification

### Output
- Production approval workflow
- Approval UI + API
- Tests pass

---

## 8.3. Rollback Strategy

### Mô tả
Auto rollback khi deploy fail, notify user, audit logging.

### Tasks
- [ ] **8.3.1** — Implement auto rollback service
  - Trigger: health check fail, smoke test fail, error rate spike
  - Function: `auto_rollback(deployment_id) -> rollback_status`
- [ ] **8.3.2** — Implement notify user khi rollback
  - Notify: deployment failed, rollback initiated
- [ ] **8.3.3** — Implement rollback audit logging
  - Log: reason, who triggered, result
- [ ] **8.3.4** — Implement manual rollback
  - API: POST /api/v1/deploy/rollback
  - Input: { "deployment_id": "...", "reason": "..." }
- [ ] **8.3.5** — Implement rollback verification
  - Verify rollback thành công
  - Function: `verify_rollback(rollback_id) -> result`
- [ ] **8.3.6** — Unit test cho rollback strategy
  - Test auto rollback
  - Test manual rollback
  - Test notification
  - Test audit logging
  - Test rollback verification

### Output
- Rollback strategy hoạt động
- Auto + manual rollback
- Tests pass

---

## 8.4. CI/CD Pipeline

### Mô tả
Setup GitHub Actions pipeline cho automated testing, build, deploy.

### Tasks
- [ ] **8.4.1** — Setup GitHub Actions workflow
  - File: `.github/workflows/ci.yml`
  - Stages: lint, test, build, deploy
- [ ] **8.4.2** — Implement automated testing trong CI
  - Run unit tests, integration tests
  - Fail pipeline nếu tests fail
- [ ] **8.4.3** — Implement automated build trong CI
  - Build Docker image
  - Push to registry
- [ ] **8.4.4** — Implement automated staging deploy trong CI
  - Deploy to staging nếu tests pass
  - Run smoke tests
- [ ] **8.4.5** — Implement CI/CD status callback
  - Callback kết quả đến workflow engine
  - Function: `handle_ci_callback(pipeline_id, result) -> state_update`
- [ ] **8.4.6** — Test CI/CD pipeline
  - Trigger pipeline
  - Verify stages
  - Verify callback

### Output
- CI/CD pipeline hoạt động
- Automated testing, build, deploy
- Tests pass

---

## 8.5. Container Orchestration

### Mô tả
Setup Docker Compose cho development, Kubernetes cho production.

### Tasks
- [ ] **8.5.1** — Setup Docker Compose cho development
  - Services: fastapi, postgres, redis, sandbox, dashboard
  - Networks: internal, external
  - Volumes: data persistence
- [ ] **8.5.2** — Setup Kubernetes manifests cho production (optional)
  - Deployment, Service, Ingress manifests
  - ConfigMap, Secret
- [ ] **8.5.3** — Implement health checks
  - Health check endpoint: /health
  - Config: interval, timeout, retries
- [ ] **8.5.4** — Implement auto-restart policies
  - Policy: on-failure, always, unless-stopped
- [ ] **8.5.5** — Implement resource limits
  - CPU, RAM limits per service
- [ ] **8.5.6** — Test container orchestration
  - Test docker-compose up
  - Test health checks
  - Test auto-restart
  - Test resource limits

### Output
- Container orchestration hoạt động
- Health checks, auto-restart, resource limits
- Tests pass

---

## 8.6. Reverse Proxy & Cloud

### Mô tả
Setup Nginx reverse proxy, SSL/TLS, deploy lên cloud.

### Tasks
- [ ] **8.6.1** — Setup Nginx reverse proxy
  - Config: upstream servers, routing, load balancing
  - File: `nginx.conf`
- [ ] **8.6.2** — Setup SSL/TLS
  - Certbot + Let's Encrypt
  - Auto-renewal
- [ ] **8.6.3** — Deploy lên cloud (AWS / Hetzner / GCP)
  - Provision server
  - Setup Docker, docker-compose
  - Deploy services
- [ ] **8.6.4** — Configure DNS
  - DNS records: A, CNAME
  - Domain: api.example.com, dashboard.example.com
- [ ] **8.6.5** — Test production deployment
  - Test health endpoints
  - Test SSL
  - Test DNS resolution
  - Test load balancing

### Output
- Production deployment hoạt động
- SSL/TLS, DNS, reverse proxy
- Tests pass

---

## 8.7. Operations Integration

### Mô tả
Tích hợp monitoring vào deployment pipeline, deployment audit logging, metrics.

### Tasks
- [ ] **8.7.1** — Tích hợp monitoring vào deployment pipeline
  - Monitor deployment health
  - Alert nếu deployment fail
- [ ] **8.7.2** — Implement deployment audit logging
  - Log: who deployed, when, what, result
- [ ] **8.7.3** — Implement deployment metrics
  - Metrics: deployment frequency, lead time, failure rate, MTTR
  - Export to Prometheus
- [ ] **8.7.4** — Integration test: deploy → monitor → rollback
  - Deploy to staging
  - Monitor health
  - Simulate failure
  - Verify rollback

### Output
- Operations integration hoàn chỉnh
- Deployment metrics
- Integration tests pass

---

## Checklist Phase 8

| # | Task | Status | Notes |
|---|---|---|---|
| 8.1 | Staging Deployment | ⬜ | Build, deploy, verify |
| 8.2 | Production Approval | ⬜ | Human approval workflow |
| 8.3 | Rollback Strategy | ⬜ | Auto + manual rollback |
| 8.4 | CI/CD Pipeline | ⬜ | GitHub Actions |
| 8.5 | Container Orchestration | ⬜ | Docker Compose / K8s |
| 8.6 | Reverse Proxy & Cloud | ⬜ | Nginx, SSL, cloud |
| 8.7 | Operations Integration | ⬜ | Monitoring, metrics |

**Definition of Done cho Phase 8:**
- [ ] Autonomous staging deploy
- [ ] Safe production deploy (human approval)
- [ ] Rollback automation
- [ ] CI/CD pipeline hoạt động
- [ ] Production deployment hoạt động
- [ ] Integration tests pass
