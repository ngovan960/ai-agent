# OpenCode Architecture

## AI SDLC Orchestrator — OpenCode Integration Design

---

## Overview

OpenCode serves as the **LLM + Tool Provider** in the system. FastAPI is the central brain; OpenCode provides:
1. LLM model access via OpenCode
2. Tool execution (bash, edit, write, read, glob, grep)
3. Sandbox environment (Docker containers)

---

## Role in Architecture

```
┌─────────────────────────────────────────────────┐
│              FastAPI (Brain)                      │
│                                                   │
│  State Machine │ Workflow │ Model Router         │
└──────────────────────┬──────────────────────────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ OpenCode  │ │ OpenCode │ │  Other   │
    │ (direct) │ │ (tools)  │ │ Providers│
    └──────────┘ └──────────┘ └──────────┘
```

---

## Tool Execution

### Available Tools
| Tool | Description | Used By |
|------|-------------|---------|
| `bash` | Execute shell commands | Specialist, Auditor, DevOps |
| `edit` | Edit file contents | Specialist |
| `write` | Create/overwrite files | Specialist |
| `read` | Read file contents | All agents |
| `glob` | Find files by pattern | All agents |
| `grep` | Search file contents | All agents |

### Tool Restrictions per Agent
| Agent | Allowed Tools |
|-------|--------------|
| Specialist | bash, edit, write, read, glob, grep |
| Auditor | bash (tests only), read, glob, grep |
| DevOps | bash, read |
| Gatekeeper/Orchestrator/Validator/Mentor/Monitoring | read, glob, grep only |

### Command Allowlist (bash tool)
```
pytest, ruff, mypy, npm, git, docker, make, curl, ls, cat, find
```

### Command Blocklist
```
rm -rf /, sudo, chmod 777, mkfs, dd, shutdown, reboot
```

---

## Execution Modes

### Dev Mode
- **Environment**: Local machine or development container
- **Tools**: Full OpenCode toolset
- **Sandbox**: None (trusted environment)
- **Use case**: Development, prototyping, fast iteration

### Production Mode
- **Environment**: Docker container (isolated)
- **Tools**: OpenCode toolset with restrictions
- **Sandbox**: Ubuntu-based container with resource limits
- **Use case**: Production deployment, untrusted code execution

### Mode Selection
- **Auto**: Based on risk level (LOW/MEDIUM → dev, HIGH/CRITICAL → prod)
- **Manual**: User can force via API
- **Default**: Dev mode for development

---

## OpenCode Verification

**File**: `services/execution/opencode_verification.py`

### Dev Mode Verification
Runs 4 checks sequentially:
1. **Lint**: ruff, flake8 (Python); eslint, tsc (Node)
2. **Test**: pytest (Python); npm test (Node)
3. **Build**: python build (Python); npm run build (Node)
4. **Security**: bandit (Python); npm audit (Node)

### Verification Flow
```
Code Output
    │
    ▼
┌─────────────────────────────────┐
│  OpenCode Verification           │
│  ┌───────────────────────────┐  │
│  │  Lint Check                │  │ ← ruff/flake8 or eslint/tsc
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Unit Test                 │  │ ← pytest or npm test
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Build Check               │  │ ← python build or npm run build
│  └────────────┬──────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Security Scan             │  │ ← bandit or npm audit
│  └───────────────────────────┘  │
│               ▼                  │
│  ┌───────────────────────────┐  │
│  │  Result: pass/fail/warning │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## Environment Variables

```bash
# OpenCode Configuration
OPENCODE_ENABLED=true
OPENCODE_SANDBOX_IMAGE=ai-sdlc-sandbox:latest

# LLM Provider (via OpenCode)
OPENCODE_API_KEY=your_api_key
OPENCODE_MODEL=deepseek/deepseek-chat
```

---

## Integration Points

| FastAPI Component | OpenCode Integration |
|-------------------|---------------------|
| Agent Runtime | LLM calls via OpenCode |
| Verification | Tool execution for lint/test/build |
| Execution Layer | Sandbox management |
| Cost Tracking | Token usage from LLM responses |

---

**Version**: 3.0.0
**Last Updated**: 2026-05-17
