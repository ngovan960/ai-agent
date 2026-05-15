from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE_ADD = "feature_add"
    REFACTOR = "refactor"
    DOC_CHANGE = "doc_change"
    ARCHITECTURAL = "architectural"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    INVESTIGATION = "investigation"


class Complexity(str, Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationVerdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class GatekeeperClassification(BaseModel):
    task_type: TaskType
    complexity: Complexity
    risk_level: RiskLevel
    estimated_effort: str = Field(..., description="e.g. '1h', '1d', '1w'")
    required_context: list[str] = Field(default_factory=list)
    suggested_agent: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str


class ValidatorVerdict(BaseModel):
    verdict: ValidationVerdict
    confidence: float = Field(..., ge=0, le=1)
    reason: str
    suggested_classification: GatekeeperClassification | None = None
    mismatch_details: list[str] = Field(default_factory=list)


class ValidationRequest(BaseModel):
    user_request: str = Field(..., min_length=1)
    gatekeeper_classification: GatekeeperClassification
    project_id: UUID | None = None
    task_id: UUID | None = None


class ValidationResponse(BaseModel):
    id: UUID
    request_id: UUID | None = None
    task_id: UUID | None = None
    verdict: ValidationVerdict
    confidence: float
    gatekeeper_classification: GatekeeperClassification
    validator_verdict: ValidatorVerdict
    final_classification: GatekeeperClassification
    action: str = Field(..., description="pass_to_orchestrator | reanalyze | escalate_to_mentor")
    created_at: str


class ValidationHistoryItem(BaseModel):
    id: UUID
    task_id: UUID | None
    verdict: ValidationVerdict
    confidence: float
    action: str
    created_at: str


class ValidationHistoryResponse(BaseModel):
    items: list[ValidationHistoryItem]
    total: int
    page: int
    page_size: int
