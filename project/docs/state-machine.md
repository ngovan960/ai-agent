# State Machine

## AI SDLC Orchestrator — Workflow State Machine

---

## Overview

**File**: `shared/config/state_transitions.py`

The workflow engine uses a state machine to manage task lifecycle. Every task progresses through a series of states, with transitions validated before execution.

---

## States (11)

| State | Description | Type |
|-------|-------------|------|
| `NEW` | Task just created | Active |
| `ANALYZING` | Gatekeeper/Orchestrator analyzing | Active |
| `PLANNING` | Orchestrator creating plan | Active |
| `IMPLEMENTING` | Specialist writing code | Active |
| `VERIFYING` | Verification pipeline running | Active |
| `REVIEWING` | Auditor reviewing output | Active |
| `ESCALATED` | Mentor takeover required | Active |
| `BLOCKED` | Waiting for dependency | Active |
| `DONE` | Task completed successfully | **Terminal** |
| `FAILED` | Task failed permanently | **Terminal** |
| `CANCELLED` | Task cancelled by user | **Terminal** |

---

## Valid Transitions (22)

| From | To | Condition |
|------|----|-----------|
| NEW | ANALYZING | Gatekeeper accepts task |
| NEW | BLOCKED | Missing dependencies |
| ANALYZING | PLANNING | Analysis complete |
| ANALYZING | NEW | Re-analysis needed |
| ANALYZING | ESCALATED | Cannot analyze |
| PLANNING | IMPLEMENTING | Plan ready, agent assigned |
| PLANNING | NEW | Plan rejected |
| PLANNING | ESCALATED | Cannot plan |
| IMPLEMENTING | VERIFYING | Code complete |
| IMPLEMENTING | ESCALATED | Implementation blocked |
| IMPLEMENTING | BLOCKED | Missing dependency |
| VERIFYING | REVIEWING | Verification passed (score ≥ 60) |
| VERIFYING | IMPLEMENTING | Verification failed (retry) |
| VERIFYING | ESCALATED | Max retries exceeded |
| REVIEWING | DONE | Auditor approves (score ≥ 0.80) |
| REVIEWING | IMPLEMENTING | Auditor requests revision |
| REVIEWING | ESCALATED | Auditor escalates |
| ESCALATED | PLANNING | Mentor approves, new plan |
| ESCALATED | FAILED | Mentor rejects |
| BLOCKED | PLANNING | Dependency resolved |
| BLOCKED | ESCALATED | Cannot resolve dependency |
| BLOCKED | FAILED | Dependency permanently blocked |

---

## Invalid Transitions

The following transitions are explicitly forbidden:

| From | To | Reason |
|------|----|--------|
| DONE | *any* | Terminal state is immutable (LAW-015) |
| FAILED | *any* | Terminal state is immutable (LAW-015) |
| CANCELLED | *any* | Terminal state is immutable (LAW-015) |
| *any* | CANCELLED | Only user can cancel |
| NEW | DONE | Must go through full workflow |
| NEW | FAILED | Must attempt processing first |
| IMPLEMENTING | DONE | Must verify and review first |
| VERIFYING | DONE | Must review first |

---

## State Transition Validation

**Function**: `validate_transition(from_state, to_state)`

```python
def validate_transition(from_state: str, to_state: str) -> tuple[bool, str]:
    # 1. Reject same-state transitions
    # 2. Validate state names exist
    # 3. Block transitions from terminal states
    # 4. Check against valid transitions list
    # 5. Check against invalid transitions list
    pass
```

---

## Terminal States

| State | Immutable | Can Be Referenced |
|-------|-----------|-------------------|
| `DONE` | Yes | Yes (for reporting) |
| `FAILED` | Yes | Yes (for reporting) |
| `CANCELLED` | Yes | Yes (for reporting) |

**LAW-015**: No terminal state can be changed once set.

---

## Workflow Engine Integration

**File**: `services/orchestrator/services/workflow_engine.py`

### Node Mapping
| State | Handler Node |
|-------|-------------|
| NEW | `_node_gatekeeper()` |
| VALIDATING | `_node_validator()` |
| ANALYZING / PLANNING | `_node_orchestrator()` |
| IMPLEMENTING | `_node_specialist()` |
| VERIFYING | `_node_verification()` |
| REVIEWING | `_node_auditor()` |
| ESCALATED | `_node_mentor()` |
| BLOCKED | `_node_blocked_handler()` |

### Per-State Retry
- Each state can retry up to `MAX_WORKFLOW_RETRIES` (2) times
- After max retries → transition to ESCALATED
- Optimistic locking prevents concurrent transition conflicts

---

## State Diagram

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
                    ▼                                              │
┌─────┐    ┌───────────┐    ┌──────────┐    ┌──────────────┐    ┌───────────┐    ┌──────┐
│ NEW │───▶│ ANALYZING │───▶│ PLANNING │───▶│ IMPLEMENTING │───▶│ VERIFYING │───▶│REVIEW │
└─────┘    └───────────┘    └──────────┘    └──────────────┘    └───────────┘    └──┬───┘
   │              │               │               │                  │               │
   │              │               │               │                  │               │
   ▼              ▼               ▼               ▼                  ▼               ▼
 BLOCKED      ESCALATED       ESCALATED       ESCALATED         IMPLEMENTING      DONE ✅
   │              │               │               │               (retry)
   │              ▼               │               │
   │         ┌────────┐           │               │
   └────────▶│ PLANNING│◀─────────┘               │
             └───┬────┘                           │
                 │                                │
                 ▼                                ▼
              FAILED ✗                        ESCALATED
                                                 │
                                                 ▼
                                            PLANNING or FAILED
```

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
**States**: 11 (8 active + 3 terminal)
**Valid Transitions**: 22
