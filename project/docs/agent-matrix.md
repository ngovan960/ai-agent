# Agent Matrix

## AI SDLC Orchestrator — Agent Responsibility Matrix

---

## Overview

The system uses **10 agent prompt templates** (8 unique agents + 2 duplicates). Each agent has a specific role, model preference, and tool access level.

---

## Agent Directory

| # | Agent | File | Role | Model | LLM Path | Tools |
|---|-------|------|------|-------|----------|-------|
| 1 | **Gatekeeper** | `agents/prompts/gatekeeper.txt` | Entry point: parse request, classify complexity (1-10), decide routing | DeepSeek V4 Flash | OpenCode | read, glob, grep |
| 2 | **Orchestrator** | `agents/prompts/orchestrator.txt` | Task breakdown, agent selection, workflow planning | Qwen 3.6 Plus | OpenCode | read, glob, grep |
| 3 | **Validator** | `agents/prompts/validator.txt` | Cross-validate Gatekeeper classification, score 5 dimensions | Qwen 3.5 Plus | OpenCode | read, glob, grep |
| 4 | **Specialist** | `agents/prompts/specialist.txt` | Write code, implement features, fix bugs | DeepSeek V4 Pro | OpenCode | bash, edit, write, read, glob, grep |
| 5 | **Coder** | `agents/prompts/coder.txt` | **Duplicate of specialist.txt** | DeepSeek V4 Pro | OpenCode | bash, edit, write, read, glob, grep |
| 6 | **Auditor** | `agents/prompts/auditor.txt` | Review code: 5-dimension scoring, law compliance check | Qwen 3.5 Plus | OpenCode | read, glob, grep |
| 7 | **Reviewer** | `agents/prompts/reviewer.txt` | **Duplicate of auditor.txt** | Qwen 3.5 Plus | OpenCode | read, glob, grep |
| 8 | **Mentor** | `agents/prompts/mentor.txt` | Strategic decisions, deadlock resolution, lesson learned | Qwen 3.6 Plus | OpenCode | read, glob, grep |
| 9 | **DevOps** | `agents/prompts/devops.txt` | Build, deploy, rollback, infrastructure | DeepSeek V4 Pro | OpenCode | bash, read |
| 10 | **Monitoring** | `agents/prompts/monitoring.txt` | System monitoring, alerting, metrics | DeepSeek V4 Flash | OpenCode | — |

---

## Agent Activation Flow

```
User Request
    │
    ▼
┌─────────────┐
│  Gatekeeper │ ← Parse, classify complexity, route
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Validator  │ ← Cross-validate classification (confidence ≥ 0.8)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Orchestrator │ ← Break down into tasks, assign agents
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Specialist  │ ← Implement code (OpenCode tools)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Verification     │ ← 5-step pipeline (lint/test/build/security)
│ Pipeline         │
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  Auditor    │ ← 5-dimension review (spec_match, structure, architecture, clean_code, law_compliance)
└──────┬──────┘
       │
       ▼
    APPROVED? ──Yes──→ DONE
       │
       No
       │
       ▼
┌─────────────┐
│   Mentor    │ ← Final verdict: APPROVED/REJECT/MODIFY
└─────────────┘
```

---

## Tool Access Matrix

| Agent | bash | edit | write | read | glob | grep |
|-------|------|------|-------|------|------|------|
| Gatekeeper | — | — | — | ✓ | ✓ | ✓ |
| Orchestrator | — | — | — | ✓ | ✓ | ✓ |
| Validator | — | — | — | ✓ | ✓ | ✓ |
| Specialist | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Auditor | ✓ (tests only) | — | — | ✓ | ✓ | ✓ |
| Mentor | — | — | — | ✓ | ✓ | ✓ |
| DevOps | ✓ | — | — | ✓ | — | — |
| Monitoring | — | — | — | — | — | — |

---

## Agent Specs

Each agent has a YAML spec in `specs/`:

| Spec File | Agent |
|-----------|-------|
| `specs/gatekeeper.yaml` | Gatekeeper |
| `specs/orchestrator.yaml` | Orchestrator |
| `specs/specialist.yaml` | Specialist |
| `specs/coder.yaml` | Coder (duplicate) |
| `specs/auditor.yaml` | Auditor |
| `specs/reviewer.yaml` | Reviewer (duplicate) |
| `specs/mentor.yaml` | Mentor |
| `specs/devops.yaml` | DevOps |
| `specs/monitoring.yaml` | Monitoring |

---

## Agent Activation Conditions

| Agent | When Activated |
|-------|---------------|
| Gatekeeper | Every new request |
| Validator | After Gatekeeper classification |
| Orchestrator | After validation passes |
| Specialist | When task is in IMPLEMENTING state |
| Auditor | When task is in REVIEWING state |
| Mentor | On ESCALATED state (retry > 2, deadlock, conflict) |
| DevOps | When task requires deployment |
| Monitoring | Continuous (background) |

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
**Agents**: 10 prompt templates (8 unique + 2 duplicates)
