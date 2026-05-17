import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

logger = logging.getLogger(__name__)


class MentorAction(Enum):
    REWRITE = "rewrite"
    REDESIGN = "redesign"
    OVERRIDE = "override"
    ESCALATE = "escalate"


@dataclass
class MentorResult:
    task_id: UUID
    mentor_id: UUID
    action: MentorAction
    reason: str
    output_state: str
    created_at: str


async def mentor_takeover(db=None, task_id=None, mentor_id=None, action=None, reason=""):
    from uuid import UUID as _UUID
    task_uuid = _UUID(task_id) if isinstance(task_id, str) else task_id
    mentor_uuid = _UUID(mentor_id) if isinstance(mentor_id, str) else mentor_id
    action_enum = MentorAction(action) if isinstance(action, str) and action in [e.value for e in MentorAction] else MentorAction.REWRITE
    result = MentorResult(
        task_id=task_uuid, mentor_id=mentor_uuid, action=action_enum,
        reason=reason, output_state="PLANNING",
        created_at=datetime.now(UTC).isoformat(),
    )
    return True, "Takeover initiated", result
