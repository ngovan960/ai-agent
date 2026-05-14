from shared.models.base import Base
from sqlalchemy import (
    Column, String, Text, Enum, ForeignKey, Float, Integer, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import enum


class TaskStatus(str, enum.Enum):
    NEW = "NEW"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    IMPLEMENTING = "IMPLEMENTING"
    VERIFYING = "VERIFYING"
    REVIEWING = "REVIEWING"
    DONE = "DONE"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Task(Base):
    __tablename__ = "tasks"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="SET NULL"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    owner = Column(String(100))
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    confidence = Column(Float, default=0.0)
    retries = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=2)
    expected_output = Column(Text)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.LOW)
    cancellation_reason = Column(Text)
    failure_reason = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    completed_at = Column(Base.created_at.type)
    failed_at = Column(Base.created_at.type)
    cancelled_at = Column(Base.created_at.type)

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_task_confidence"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 10", name="ck_task_risk_score"),
    )

    project = relationship("Project", back_populates="tasks")
    module = relationship("Module", back_populates="tasks")
    outputs = relationship("TaskOutput", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    depended_by = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
    )
    retry_records = relationship("Retry", back_populates="task", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="task")
    mentor_instructions = relationship("MentorInstruction", back_populates="task")
    decisions = relationship("Decision", back_populates="task")
    deployments = relationship("Deployment", back_populates="task")
    cost_records = relationship("CostTracking", back_populates="task")
    llm_call_logs = relationship("LLMCallLog", back_populates="task")


class TaskOutput(Base):
    __tablename__ = "task_outputs"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    output_type = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False, default=lambda: {})

    task = relationship("Task", back_populates="outputs")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(50), nullable=False, default="blocks")

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dep"),
    )

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="depended_by")
