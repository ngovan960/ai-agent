---
agent: system
role: "System-level operating protocol — agent coordination, handoff rules, conflict resolution, governance"
version: "5.1.0"
---

# AI SDLC System Operating Protocol

This is the master operating protocol for the entire AI SDLC agent system. Every agent must follow these rules. Individual agent skills define role-specific behavior; this document defines cross-agent rules.

## Agent Communication Protocol

### Handoff Rules
When one agent hands off to another:
```
1. Include full context — never assume the next agent knows what you know
2. State your confidence level — be honest about uncertainty
3. Flag edge cases — things that might go wrong
4. Keep output structured — JSON for machine-readable, text for human-readable
```

### Disagreement Protocol
When agents disagree:
```
Gatekeeper vs Validator:
    → Validator wins (Validator is the check on Gatekeeper)
    → If Validator confidence < 0.8: re-analyze (back to Gatekeeper)
    → If Validator confidence < 0.5: escalate to Mentor

Specialist vs Auditor:
    → Auditor wins on quality/law compliance
    → Specialist wins on feasibility (can this be built?)
    → If deadlock: escalate to Mentor

Orchestrator vs Specialist:
    → Orchestrator wins on "what to build"
    → Specialist wins on "how to build it"
    → If feasibility conflict: escalate to Mentor

Any agent vs Mentor:
    → Mentor ALWAYS wins (supreme authority)
```

### Escalation Rules
```
Escalate to Mentor when:
1. Retry count > 2 for any state
2. Agent conflict cannot be resolved
3. Architectural law violation detected
4. Task deadlocked > 30 minutes
5. Security vulnerability found
6. Data corruption suspected
```

## Workflow Pipeline

```
User Request
    ↓
[GATEKEEPER] — Classify intent, complexity, risk
    ↓ (LOW+TRIVIAL: skip validation)
[VALIDATOR] — Cross-validate classification
    ↓ (APPROVED)              ↓ (REJECTED)
[ORCHESTRATOR] — Plan       [MENTOR] — Resolve
    ↓                            ↓
[ORCHESTRATOR] — Assign     [ORCHESTRATOR] — Replan
    ↓
[SPECIALIST] — Code          ← (REVISE from Auditor)
    ↓                         ← (retry ≤2 from Verification)
[VERIFICATION] — Test
    ↓ (PASS)    ↓ (FAIL)
[AUDITOR] — Review    [retry or escalate]
    ↓
[DONE] → [DEVOPS] — Deploy (if requested)
              ↓
         [MONITORING] — Observe
```

## State Flow Diagram
```
NEW ─→ VALIDATING ─→ ANALYZING ─→ PLANNING ─→ IMPLEMENTING
 │         │              │            │              │
 │         ├─→ ESCALATED  │            │              │
 │         └─→ NEW        │            │              │
 │                        │            │              │
 └──→ BLOCKED ←───────────┴────────────┘              │
      │    │                                          │
      │    └──→ CANCELLED                             │
      │                                               │
      └──→ PLANNING (dep resolved)                    │
                                                      │
IMPLEMENTING ─→ VERIFYING ─→ REVIEWING ─→ DONE        │
      ↑                        │    │                  │
      │                        │    ├─→ ESCALATED      │
      │                        │    └─→ CANCELLED      │
      └──── (retry≤2) ─────────┘                       │
      └──── (REVISE) ──────────────────────────────────┘

ESCALATED ─→ PLANNING (redesign)
         ─→ IMPLEMENTING (rewrite)
         ─→ VERIFYING (override)
         ─→ FAILED (reject)
         ─→ DONE (approve)

TERMINAL: DONE | FAILED | CANCELLED (immutable)
```

## Architectural Laws (Summary)

Every agent must comply. Full text: `governance/laws.yaml`

### CRITICAL Severity (immediate escalation if violated)
- LAW-004: Production deploys require human approval
- LAW-005: No hardcoded secrets or credentials
- LAW-009: No DONE without verification pass
- LAW-013: Dual-model validation for MEDIUM+ risk tasks

### HIGH Severity (must fix before approval)
- LAW-001: No business logic in controllers
- LAW-002: All APIs validate input (Pydantic)
- LAW-003: No direct DB access from routes
- LAW-006: All errors logged
- LAW-008: No architecture changes without approval
- LAW-010: No infinite retry loops
- LAW-015: Circuit breaker enforced per model
- LAW-018: Agent role boundaries enforced

### MEDIUM Severity (should fix, approval possible with note)
- LAW-007: API response < 3s (p95)
- LAW-011: Scope adherence required
- LAW-012: All state changes audited
- LAW-014: Terminal states are immutable
- LAW-016: Mentor quota enforced (10/day)
- LAW-017: All LLM calls tracked
- LAW-019: Confidence scores in [0, 1]
- LAW-020: Risk-based execution mode

## Agent Capability Matrix

| Agent | Write Code | Read Code | Run Bash | LLM Calls | Deploy |
|---|---|---|---|---|---|
| Gatekeeper | ❌ | ❌ | ❌ | ✅ LiteLLM | ❌ |
| Validator | ❌ | ❌ | ❌ | ✅ LiteLLM | ❌ |
| Orchestrator | ❌ | ✅ | ❌ | ✅ LiteLLM | ❌ |
| Specialist | ✅ | ✅ | ✅ | ✅ OpenCode | ❌ |
| Auditor | ❌ | ✅ | ✅ (test only) | ✅ LiteLLM | ❌ |
| Mentor | ❌ | ✅ | ✅ | ✅ LiteLLM | ❌ |
| DevOps | ✅ | ✅ | ✅ | ✅ OpenCode | ✅ |
| Monitoring | ❌ | ✅ | ✅ | ✅ LiteLLM | ❌ |

## Version History
- v5.1.0: Complete agent skill definitions, 12-state workflow, 8 agents
