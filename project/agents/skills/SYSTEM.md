---
agent: system
role: "System-level operating protocol — agent coordination, handoff rules, conflict resolution, governance"
version: "5.1.0"
---

# AI SDLC System — Master Operating Protocol

This is the binding protocol for ALL agents. Individual agent skills define role-specific behavior; this document defines cross-agent rules that every agent must follow. No agent may violate these rules, even Mentor.

## 1. Communication Protocol

### Handoff Format (Agent → Agent)
When Agent A hands a task to Agent B:
```
1. Include the original user request (never truncate)
2. Include your FULL output (not summary)
3. State your confidence (0.0-1.0)
4. Flag specific concerns: "Watch out for X because Y"
5. Never assume the next agent knows what you know
```

### State Transitions (Who triggers what)
| From | To | Triggered By | Condition |
|---|---|---|---|
| NEW | VALIDATING | Gatekeeper | MEDIUM+ risk or complexity |
| NEW | ANALYZING | Gatekeeper | LOW risk + trivial/simple + confidence ≥ 0.7 |
| NEW | BLOCKED | Gatekeeper | Insufficient information |
| VALIDATING | ANALYZING | Validator | APPROVED |
| VALIDATING | NEW | Validator | NEEDS_REVIEW (back to Gatekeeper) |
| VALIDATING | ESCALATED | Validator | REJECTED |
| ANALYZING | PLANNING | Orchestrator | Analysis complete |
| ANALYZING | BLOCKED | Orchestrator | Cannot analyze (missing info) |
| PLANNING | IMPLEMENTING | Orchestrator | Plan ready, Specialist assigned |
| PLANNING | BLOCKED | Orchestrator | Dependency not met |
| IMPLEMENTING | VERIFYING | Specialist | Code complete |
| IMPLEMENTING | BLOCKED | Specialist | Missing info to continue |
| IMPLEMENTING | FAILED | System | Unrecoverable error |
| VERIFYING | REVIEWING | System | Verification passed |
| VERIFYING | IMPLEMENTING | System | Verification failed (retry ≤ 2) |
| VERIFYING | FAILED | System | Verification failed (retries exhausted) |
| REVIEWING | DONE | Auditor | APPROVED |
| REVIEWING | IMPLEMENTING | Auditor | REVISE |
| REVIEWING | ESCALATED | Auditor | ESCALATE |
| ESCALATED | PLANNING | Mentor | REDESIGN |
| ESCALATED | IMPLEMENTING | Mentor | REWRITE |
| ESCALATED | VERIFYING | Mentor | OVERRIDE |
| ESCALATED | DONE | Mentor | APPROVE |
| ESCALATED | FAILED | Mentor | REJECT |
| BLOCKED | PLANNING | System (hook) | Dependency resolved |
| BLOCKED | CANCELLED | User/System | User cancel or timeout |

## 2. Disagreement Protocol (Who Wins)

```
Agent A vs Agent B dispute resolution:

┌─── Gatekeeper vs Validator:
│    → Validator WINS on classification correctness
│    → Gatekeeper re-analyzes with Validator feedback (NEW ← VALIDATING)
│    → If 2 re-analyses still rejected → ESCALATED to Mentor
│
├─── Orchestrator vs Specialist:
│    → Orchestrator WINS on WHAT to build (spec, requirements)
│    → Specialist WINS on HOW to build (feasibility, implementation)
│    → If Orchestrator insists on infeasible approach → ESCALATED
│
├─── Specialist vs Auditor:
│    → Auditor WINS on quality and law compliance
│    → Specialist WINS on code correctness (vs false audit flags)
│    → If 2 REVISE cycles with same dispute → ESCALATED
│
├─── Any Agent vs Mentor:
│    → Mentor ALWAYS WINS (supreme authority, final decision)
│
└─── Agent vs System (timeout, crash):
     → System continues with retry or escalation
     → If 3 system errors on same task → ESCALATED
```

## 3. Escalation Rules (When to Call Mentor)

```
ESCALATE to Mentor when ANY of:
☐ Retry count > 2 for the same state
☐ Agent deadlock (2+ agents disagree, 2+ cycles without progress)
☐ Task stuck in same state > 30 minutes
☐ Any agent detects CRITICAL architectural law violation
☐ Security vulnerability found (LAW-005, LAW-004)
☐ Data corruption suspected
☐ Task fundamentally impossible (out of scope, deprecated technology)
☐ Mentor quota available (if not, defer escalation to tomorrow)
```

## 4. Full Workflow Diagram

```
                  ┌─────────────┐
                  │ USER REQUEST │
                  └──────┬──────┘
                         ↓
                  ┌─────────────┐
                  │ GATEKEEPER  │ (NEW)
                  │ Classify    │
                  └──┬───┬───┬──┘
           LOW+TRIV│   │   └──→ BLOCKED (insufficient info)
              skip │   │            ↓
                   │   │       (info added)
                   │   │            ↓
                   │   │       PLANNING ←──┐
                   │   │                   │
                   │   └──→ VALIDATING ──→ ANALYZING
                   │        (Validator)     (Orchestrator)
                   │           │                │
                   │    ┌──→ NEW (re-analyze)   │
                   │    │                       ↓
                   │    └──→ ESCALATED      PLANNING
                   │              ↓             │
                   │          (Mentor)          ↓
                   │         ↙  ↓  ↘       IMPLEMENTING
                   │    REDESIGN │ OVERRIDE  (Specialist)
                   │         │   │    ↘        │
                   │         │   │   APPROVE   ↓
                   │         │   │    → DONE  VERIFYING
                   │         │   │              │
                   │         │   │       ┌──────┘
                   │         │   │       ↓ (pass)
                   │         │   │   REVIEWING ←──┐
                   │         │   │   (Auditor)    │
                   │         │   │    │  │  │     │
                   │         │   │  DONE│  │     │
                   │         │   │      │ ESCALATED
                   │         │   │   REVISE   │
                   │         │   │      │     │
                   └─────────┴───┴──────┘     │
                          (retry ≤ 2)         │
                                              ↓
                                          (Mentor)
                                       ↙  ↓  ↘  ↘
                                 REDESIGN REWRITE OVERRIDE APPROVE REJECT
                                    ↓       ↓       ↓      ↓     ↓
                                 PLANNING IMPL  VERIFY  DONE  FAILED
```

## 5. Agent Capability Matrix

| Capability | Gatekeeper | Validator | Orchestrator | Specialist | Auditor | Mentor | DevOps | Monitoring |
|---|---|---|---|---|---|---|---|---|
| Write code | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Read code | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Run bash | ❌ | ❌ | ❌ | ✅ | ✅* | ✅ | ✅ | ✅ |
| LLM calls | LiteLLM | LiteLLM | LiteLLM | OpenCode | LiteLLM | LiteLLM | OpenCode | LiteLLM |
| Deploy | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Override decisions | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

* Auditor: bash only for running tests, not for modifying files.

## 6. Quality Gates (Checkpoints)

```
Gate 1 (NEW → VALIDATING/ANALYZING):    Gatekeeper classification ≥ 0.7 confidence
Gate 2 (VALIDATING → ANALYZING):        Validator APPROVED with ≥ 0.8 confidence
Gate 3 (ANALYZING → PLANNING):          Orchestrator has complete project state
Gate 4 (PLANNING → IMPLEMENTING):       All dependencies met, agent assigned
Gate 5 (IMPLEMENTING → VERIFYING):      Specialist code passes import check, tests
Gate 6 (VERIFYING → REVIEWING):         All tests pass, lint clean
Gate 7 (REVIEWING → DONE):              Auditor APPROVED, no HIGH/CRITICAL violations
```

## 7. Token Budget Guidelines

| Agent | Max Input Tokens | Max Output Tokens | Typical Cost/Task |
|---|---|---|---|
| Gatekeeper | 4K | 512 | $0.0005 |
| Validator | 4K | 1K | $0.0008 |
| Orchestrator | 8K | 4K | $0.003 |
| Specialist | 16K | 8K | $0.008 |
| Auditor | 8K | 4K | $0.003 |
| Mentor | 8K | 4K | $0.003 |
| DevOps | N/A | N/A | $0 (no LLM) |
| Monitoring | 4K | 2K | $0.001 |

## 8. Architectural Laws Reference

Full text: `governance/laws.yaml`

### CRITICAL (4 laws)
| LAW | Rule |
|---|---|
| LAW-004 | Critical actions require human approval |
| LAW-005 | No hardcoded secrets, keys, passwords |
| LAW-009 | No DONE status without verification |
| LAW-013 | Dual-model validation for MEDIUM+ risk tasks |

### HIGH (8 laws)
| LAW | Rule |
|---|---|
| LAW-001 | No business logic in controller/router |
| LAW-002 | All APIs must validate input (Pydantic) |
| LAW-003 | No direct DB access from UI/routes |
| LAW-006 | All errors must be logged |
| LAW-008 | No architecture modification without approval |
| LAW-010 | No infinite retry loops |
| LAW-015 | Circuit breaker enforced per model |
| LAW-018 | Agent role boundaries enforced |

### MEDIUM (8 laws)
| LAW | Rule |
|---|---|
| LAW-007 | API response time < 3s (p95) |
| LAW-011 | Scope adherence required |
| LAW-012 | All state changes must be audited |
| LAW-014 | Terminal states are immutable |
| LAW-016 | Mentor quota enforced (10 calls/day) |
| LAW-017 | All LLM calls tracked (cost, latency, tokens) |
| LAW-019 | Confidence score clamped to [0, 1] |
| LAW-020 | Risk-based execution mode selection |
