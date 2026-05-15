"""
State Transition Rules - AI SDLC System

Defines all valid state transitions for tasks in the workflow.
Version 4.0.0 — Added BLOCKED timeout escalation, optimistic locking support.
"""

VALID_TRANSITIONS = {
    "NEW": ["ANALYZING", "BLOCKED", "VALIDATING"],
    "VALIDATING": ["ANALYZING", "NEW", "ESCALATED", "BLOCKED"],
    "ANALYZING": ["PLANNING", "BLOCKED", "CANCELLED"],
    "PLANNING": ["IMPLEMENTING", "BLOCKED", "CANCELLED"],
    "IMPLEMENTING": ["VERIFYING", "BLOCKED", "FAILED"],
    "VERIFYING": ["REVIEWING", "IMPLEMENTING", "FAILED"],
    "REVIEWING": ["DONE", "IMPLEMENTING", "ESCALATED", "CANCELLED"],
    "ESCALATED": ["PLANNING", "FAILED", "DONE"],
    "BLOCKED": ["PLANNING", "CANCELLED", "ESCALATED"],
    "DONE": [],
    "FAILED": [],
    "CANCELLED": [],
}

TERMINAL_STATES = {"DONE", "FAILED", "CANCELLED"}

TRANSITION_CONDITIONS = {
    ("NEW", "ANALYZING"): "Gatekeeper da phan loai task (skip validation cho LOW+TRIVIAL)",
    ("NEW", "VALIDATING"): "Gatekeeper phan loai xong, can Validator cross-validate",
    ("NEW", "BLOCKED"): "Thieu thong tin de phan tich",
    ("VALIDATING", "ANALYZING"): "Validator APPROVED avec confidence >= 0.8",
    ("VALIDATING", "NEW"): "Validator APPROVED nhung confidence < 0.8, can re-analyze",
    ("VALIDATING", "ESCALATED"): "Validator REJECTED hoac NEEDS_REVIEW",
    ("VALIDATING", "BLOCKED"): "Validation loi, khong the tiep tuc",
    ("ANALYZING", "PLANNING"): "Orchestrator da chia task",
    ("ANALYZING", "BLOCKED"): "Khong the phan tich do thieu thong tin",
    ("ANALYZING", "CANCELLED"): "User huy task",
    ("PLANNING", "IMPLEMENTING"): "Agent da nhan task va context",
    ("PLANNING", "BLOCKED"): "Dependency chua hoan thanh",
    ("PLANNING", "CANCELLED"): "User huy task",
    ("IMPLEMENTING", "VERIFYING"): "Code da hoan thanh, dua vao sandbox",
    ("IMPLEMENTING", "BLOCKED"): "Thieu thong tin de tiep tuc",
    ("IMPLEMENTING", "FAILED"): "Loi khong phuc hoi duoc",
    ("VERIFYING", "REVIEWING"): "Sandbox pass (lint, test, build, security)",
    ("VERIFYING", "IMPLEMENTING"): "Sandbox fail, retry count < max_retries",
    ("VERIFYING", "FAILED"): "Verification that bai nghiem trong va da het retry",
    ("REVIEWING", "DONE"): "Auditor approve (confidence >= threshold)",
    ("REVIEWING", "IMPLEMENTING"): "Auditor revise (confidence < threshold)",
    ("REVIEWING", "ESCALATED"): "Auditor escalate (critical violation)",
    ("REVIEWING", "CANCELLED"): "User huy task",
    ("ESCALATED", "PLANNING"): "Mentor takeover, tao plan moi",
    ("ESCALATED", "FAILED"): "Mentor reject task",
    ("ESCALATED", "DONE"): "Task co verified output (LAW-009 exception) — Mentor approved bypass",
    ("BLOCKED", "PLANNING"): "Dependency da hoan thanh",
    ("BLOCKED", "CANCELLED"): "User huy task",
    ("BLOCKED", "ESCALATED"): "BLOCKED timeout (120+ minutes) — auto-escalate to Mentor",
}

INVALID_TRANSITIONS = [
    ("DONE", "ANY", "Task da hoan thanh, khong duoc sua doi"),
    ("FAILED", "ANY", "Task da that bai vinh vien, khong duoc chuyen"),
    ("CANCELLED", "ANY", "Task da huy, khong duoc chuyen"),
    ("VERIFYING", "PLANNING", "Phai qua retry/escalate, khong duoc quay lai planning"),
    ("VERIFYING", "ANALYZING", "Phai qua retry/escalate"),
    ("VERIFYING", "REVIEWING", "Chi duoc khi sandbox pass"),
    ("REVIEWING", "PLANNING", "Phai qua retry (IMPLEMENTING), khong duoc skip verify"),
    ("REVIEWING", "VERIFYING", "Da qua verify roi, khong duoc quay lai"),
    ("REVIEWING", "ANALYZING", "Phai qua retry (IMPLEMENTING)"),
    ("ESCALATED", "IMPLEMENTING", "Phai qua Mentor takeover (PLANNING)"),
    ("ESCALATED", "VERIFYING", "Phai qua IMPLEMENTING truoc"),
    ("ESCALATED", "REVIEWING", "Phai qua IMPLEMENTING → VERIFYING truoc"),
    ("BLOCKED", "IMPLEMENTING", "Phai qua PLANNING truoc"),
    ("BLOCKED", "VERIFYING", "Phai qua PLANNING va IMPLEMENTING truoc"),
    ("BLOCKED", "REVIEWING", "Phai qua PLANNING, IMPLEMENTING, VERIFYING truoc"),
    ("BLOCKED", "DONE", "Phai qua toan bo workflow truoc"),
    ("NEW", "DONE", "Phai qua toan bo workflow truoc"),
    ("NEW", "IMPLEMENTING", "Phai qua ANALYZING va PLANNING truoc"),
    ("NEW", "VERIFYING", "Phai qua toan bo workflow"),
    ("NEW", "REVIEWING", "Phai qua toan bo workflow"),
    ("ANY", "DONE", "Chi REVIEWING → DONE duoc (hoac EXCEPTION: ESCALATED → DONE voi verified output)"),
]


def validate_transition(current_status: str, new_status: str, has_verified_output: bool = False) -> tuple[bool, str]:
    """
    Validate if a state transition is allowed.

    Args:
        current_status: Current task status
        new_status: Desired new status
        has_verified_output: Whether task has a passed verification (for ESCALATED → DONE)

    Returns:
        Tuple of (is_valid, reason)
    """
    if current_status == new_status:
        return False, "Cannot transition to the same status"

    if current_status not in VALID_TRANSITIONS:
        return False, f"Unknown status: {current_status}"

    if new_status not in VALID_TRANSITIONS:
        return False, f"Unknown status: {new_status}"

    if current_status in TERMINAL_STATES:
        return False, f"Task is in terminal state {current_status}, cannot transition"

    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        for from_status, to_status, reason in INVALID_TRANSITIONS:
            if from_status == current_status and to_status == new_status:
                return False, reason
            if from_status == "ANY" and to_status == new_status:
                return False, reason
        return False, f"Invalid transition: {current_status} -> {new_status}"

    if current_status == "ESCALATED" and new_status == "DONE" and not has_verified_output:
        return False, "ESCALATED -> DONE requires verified output (LAW-009). Task must have passed verification before escalation."

    condition = TRANSITION_CONDITIONS.get(
        (current_status, new_status), "No condition defined"
    )
    return True, condition


def is_terminal(status: str) -> bool:
    """Check if a status is a terminal state."""
    return status in TERMINAL_STATES


def get_valid_transitions(status: str) -> list[str]:
    """Get all valid next states for a given status."""
    return VALID_TRANSITIONS.get(status, [])


def get_transition_condition(from_status: str, to_status: str) -> str:
    """Get the condition description for a transition."""
    return TRANSITION_CONDITIONS.get(
        (from_status, to_status), "No condition defined"
    )


VALIDATION_REQUIRED_FOR_NEW_TO_ANALYZING = True

VALIDATION_SKIP_CONDITIONS = {
    "risk_level": ["low"],
    "complexity": ["trivial", "simple"],
}


def requires_validation(
    risk_level: str,
    complexity: str,
) -> bool:
    """Check if a NEW → ANALYZING transition requires dual-model validation."""
    if not VALIDATION_REQUIRED_FOR_NEW_TO_ANALYZING:
        return False
    skip_risks = VALIDATION_SKIP_CONDITIONS.get("risk_level", [])
    skip_complexities = VALIDATION_SKIP_CONDITIONS.get("complexity", [])
    if risk_level.lower() in skip_risks and complexity.lower() in skip_complexities:
        return False
    return True


def validate_transition_with_gatecheck(
    current_status: str,
    new_status: str,
    has_validated: bool = False,
    risk_level: str = "low",
    complexity: str = "simple",
    has_verified_output: bool = False,
) -> tuple[bool, str]:
    """
    Validate state transition with dual-model validation gatecheck.

    For NEW → ANALYZING: requires validation approval unless risk=low AND complexity=trivial/simple.

    Args:
        current_status: Current task status
        new_status: Desired new status
        has_validated: Whether dual-model validation passed (for NEW → ANALYZING)
        risk_level: Task risk level (low/medium/high/critical)
        complexity: Task complexity (trivial/simple/medium/complex/critical)
        has_verified_output: Whether task has a passed verification (for ESCALATED → DONE)

    Returns:
        Tuple of (is_valid, reason)
    """
    if current_status == "NEW" and new_status == "ANALYZING":
        if requires_validation(risk_level, complexity) and not has_validated:
            return False, "NEW → ANALYZING requires dual-model validation approval. Submit to /api/v1/validation first."

    return validate_transition(current_status, new_status, has_verified_output)


BLOCKED_TIMEOUT_MINUTES = 120
BLOCKED_WARNING_MINUTES = 60
STUCK_TASK_TIMEOUT_MINUTES = 30
STUCK_TASK_ESCALATION_MINUTES = 60


def get_blocked_timeout_minutes() -> int:
    """Get the timeout in minutes before BLOCKED tasks are auto-escalated."""
    return BLOCKED_TIMEOUT_MINUTES


def get_blocked_warning_minutes() -> int:
    """Get the timeout in minutes before BLOCKED warning is sent."""
    return BLOCKED_WARNING_MINUTES


def should_send_blocked_warning(minutes_blocked: int) -> bool:
    """Check if a blocked warning should be sent."""
    return minutes_blocked >= BLOCKED_WARNING_MINUTES


def should_auto_escalate_blocked(minutes_blocked: int) -> bool:
    """Check if a BLOCKED task should be auto-escalated."""
    return minutes_blocked >= BLOCKED_TIMEOUT_MINUTES