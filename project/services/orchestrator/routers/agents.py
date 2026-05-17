
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentStatus(BaseModel):
    name: str
    role: str
    status: str
    current_task: str | None = None
    total_calls: int = 0
    success_rate: float = 0.0
    last_active: str | None = None


AGENTS = [
    AgentStatus(name="Gatekeeper", role="Input Validation", status="idle", total_calls=0),
    AgentStatus(name="Orchestrator", role="Planning & Coordination", status="idle", total_calls=0),
    AgentStatus(name="Architect", role="System Design", status="idle", total_calls=0),
    AgentStatus(name="Mentor", role="Code Review & Guidance", status="idle", total_calls=0),
    AgentStatus(name="Specialist", role="Implementation", status="idle", total_calls=0),
    AgentStatus(name="Auditor", role="Verification & Testing", status="idle", total_calls=0),
    AgentStatus(name="Deployer", role="Deployment & Rollback", status="idle", total_calls=0),
]


@router.get("/", response_model=list[AgentStatus])
async def list_agents():
    return AGENTS
