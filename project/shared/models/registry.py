from shared.models.base import Base
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Float, Integer, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import enum


class AuditResult(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class InstructionType(str, enum.Enum):
    ADVICE = "advice"
    WARNING = "warning"
    DECISION = "decision"
    PATTERN = "pattern"


class LLMCallStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class Retry(Base):
    __tablename__ = "retries"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=False)
    output = Column(JSON, default=lambda: {})
    error_log = Column(Text)

    task = relationship("Task", back_populates="retry_records")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False)
    actor_type = Column(String(50), nullable=False, default="agent")
    input = Column(JSON, default=lambda: {})
    output = Column(JSON, default=lambda: {})
    result = Column(Enum(AuditResult), nullable=False)
    message = Column(Text)

    task = relationship("Task", back_populates="audit_logs")


class MentorInstruction(Base):
    __tablename__ = "mentor_instructions"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    instruction_type = Column(Enum(InstructionType), nullable=False)
    content = Column(Text, nullable=False)
    context = Column(JSON, default=lambda: {})
    applied = Column(Boolean, nullable=False, default=False)
    embedding = Column("embedding", String)

    task = relationship("Task", back_populates="mentor_instructions")


class MentorQuota(Base):
    __tablename__ = "mentor_quota"

    date = Column(Date, nullable=False, unique=True)
    calls_used = Column(Integer, nullable=False, default=0)
    calls_limit = Column(Integer, nullable=False, default=10)


class Decision(Base):
    __tablename__ = "decisions"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    decision = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    context = Column(JSON, default=lambda: {})
    alternatives = Column(JSON, default=lambda: [])
    decided_by = Column(String(100), nullable=False, default="mentor")

    project = relationship("Project", back_populates="decisions")
    task = relationship("Task", back_populates="decisions")


class Workflow(Base):
    __tablename__ = "workflows"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="RUNNING")
    current_node = Column(String(100))
    graph = Column(JSON, default=lambda: {})
    state = Column(JSON, default=lambda: {})
    started_at = Column(Base.created_at.type)
    completed_at = Column(Base.created_at.type)
    error = Column(Text)

    project = relationship("Project", back_populates="workflows")


class DeploymentEnv(str, enum.Enum):
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Deployment(Base):
    __tablename__ = "deployments"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    environment = Column(Enum(DeploymentEnv), nullable=False, default=DeploymentEnv.STAGING)
    image_tag = Column(String(255), nullable=False)
    status = Column(Enum(DeploymentStatus), nullable=False, default=DeploymentStatus.PENDING)
    url = Column(String(500))
    logs = Column(Text)
    deployed_by = Column(String(100))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    completed_at = Column(Base.created_at.type)

    task = relationship("Task", back_populates="deployments")


class CostTracking(Base):
    __tablename__ = "cost_tracking"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    agent_name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Integer, nullable=False, default=0)
    status = Column(Enum(LLMCallStatus), nullable=False, default=LLMCallStatus.COMPLETED)
    error_message = Column(Text)

    task = relationship("Task", back_populates="cost_records")
    project = relationship("Project")


class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    cost_tracking_id = Column(UUID(as_uuid=True), ForeignKey("cost_tracking.id", ondelete="SET NULL"))
    agent_name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_hash = Column(String(64))
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    status = Column(Enum(LLMCallStatus), nullable=False, default=LLMCallStatus.COMPLETED)
    error_message = Column(Text)
    retry_count = Column(Integer, nullable=False, default=0)
    circuit_breaker_triggered = Column(Boolean, nullable=False, default=False)

    task = relationship("Task", back_populates="llm_call_logs")


class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_state"

    model = Column(String(100), nullable=False, unique=True)
    state = Column(String(20), nullable=False, default="closed")
    failure_count = Column(Integer, nullable=False, default=0)
    last_failure_at = Column(Base.created_at.type)
    last_success_at = Column(Base.created_at.type)
    half_open_at = Column(Base.created_at.type)


class EmbeddingConfig(Base):
    __tablename__ = "embedding_config"

    model_name = Column(String(255), nullable=False, unique=True)
    provider = Column(String(100), nullable=False)
    dimensions = Column(Integer, nullable=False, default=1536)
    cost_per_1k_input_tokens = Column(Float, nullable=False, default=0.0)
    cost_per_1k_output_tokens = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
