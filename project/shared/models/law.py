import enum

from sqlalchemy import Column, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.models.base import Base


class LawSeverity(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


class LawViolation(Base):
    __tablename__ = "law_violations"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    law_id = Column(String(50), nullable=False)
    law_name = Column(String(255), nullable=False)
    severity = Column(Enum(LawSeverity, name="law_severity"), nullable=False)
    violation_details = Column(Text, nullable=False)
    location = Column(String(500))

    task = relationship("Task", back_populates="law_violations")
