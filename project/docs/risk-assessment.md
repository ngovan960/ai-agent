# Risk Assessment

## AI SDLC Orchestrator — Risks & Mitigations

---

## Risk Classification

**File**: `services/orchestrator/services/risk_classifier.py`

### 4-Axis Scoring
| Axis | Range | Weight |
|------|-------|--------|
| Complexity | 1-10 | 0.5 |
| Data Sensitivity | 0-3 | 1.0 |
| User Impact | 0-3 | 1.0 |
| Deployment Scope | 0-2 | 1.25 |

### Risk Levels
| Score | Level | Action | Workflow Path |
|-------|-------|--------|---------------|
| ≤ 3 | LOW | Auto-approve | Fast track |
| ≤ 6 | MEDIUM | Require audit | Standard |
| ≤ 8 | HIGH | Senior review + audit | Review gate |
| > 8 | CRITICAL | Human approval required | Full review |

---

## System Risks

### R1: LLM Hallucination
| Aspect | Detail |
|--------|--------|
| **Risk** | AI generates incorrect code or decisions |
| **Impact** | HIGH |
| **Likelihood** | MEDIUM |
| **Mitigation** | 5-step verification pipeline, 5-dimension auditor review, 20 architectural laws, confidence scoring |
| **Residual Risk** | LOW |

### R2: Cost Overrun
| Aspect | Detail |
|--------|--------|
| **Risk** | LLM costs exceed budget |
| **Impact** | MEDIUM |
| **Likelihood** | MEDIUM |
| **Mitigation** | Per-call cost tracking, Dynamic Model Router (cost-aware), mentor quota (10/day), Prometheus cost alerts |
| **Residual Risk** | LOW |

### R3: Infinite Retry Loops
| Aspect | Detail |
|--------|--------|
| **Risk** | Tasks retry indefinitely |
| **Impact** | HIGH |
| **Likelihood** | LOW |
| **Mitigation** | LAW-010: Max 2 retries, then escalate to Mentor. Workflow engine enforces limit. |
| **Residual Risk** | VERY LOW |

### R4: Security Breach
| Aspect | Detail |
|--------|--------|
| **Risk** | AI executes malicious code or exposes secrets |
| **Impact** | CRITICAL |
| **Likelihood** | LOW |
| **Mitigation** | LAW-005: No hardcoded secrets, no eval/exec. Sandbox isolation. Command allowlist/blocklist. |
| **Residual Risk** | LOW |

### R5: Data Loss
| Aspect | Detail |
|--------|--------|
| **Risk** | Database corruption or loss |
| **Impact** | CRITICAL |
| **Likelihood** | VERY LOW |
| **Mitigation** | PostgreSQL WAL, regular backups, Docker volume persistence, snapshot restore capability |
| **Residual Risk** | VERY LOW |

### R6: Model Availability
| Aspect | Detail |
|--------|--------|
| **Risk** | LLM API goes down |
| **Impact** | HIGH |
| **Likelihood** | MEDIUM |
| **Mitigation** | Circuit breaker per model, fallback model chain, retry with exponential backoff |
| **Residual Risk** | MEDIUM |

### R7: State Machine Corruption
| Aspect | Detail |
|--------|--------|
| **Risk** | Invalid state transitions corrupt task lifecycle |
| **Impact** | HIGH |
| **Likelihood** | VERY LOW |
| **Mitigation** | LAW-015: Terminal states immutable. 22 valid transitions enforced. Optimistic locking. |
| **Residual Risk** | VERY LOW |

### R8: Mentor Quota Exhaustion
| Aspect | Detail |
|--------|--------|
| **Risk** | Mentor calls exceed daily limit |
| **Impact** | MEDIUM |
| **Likelihood** | MEDIUM |
| **Mitigation** | LAW-017: Database-enforced quota (10/day). Queue or reject if exceeded. |
| **Residual Risk** | LOW |

---

## Risk Matrix

```
Impact
  HIGH │  R1    R3    R6
       │
 MEDIUM│        R2    R8
       │
   LOW │              R4    R5    R7
       │
       └────────────────────────────
         VERY LOW   LOW   MEDIUM   HIGH
                  Likelihood
```

---

## Monitoring

| Risk | Metric | Alert Threshold |
|------|--------|-----------------|
| LLM Hallucination | Confidence score | < 0.40 average |
| Cost Overrun | Cost rate | > $0.10/hour |
| Infinite Retries | Retry rate | > 5/min |
| Model Availability | Circuit breaker state | OPEN for > 5 min |
| Mentor Quota | Remaining calls | < 2 |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
