import enum

from sqlalchemy import Column, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.models.base import Base


class ModuleStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    REVIEWING = "REVIEWING"


class Module(Base):
    __tablename__ = "modules"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ModuleStatus, name="module_status"), nullable=False, default=ModuleStatus.PENDING)

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_module_project_name"),
    )

    project = relationship("Project", back_populates="modules")
    tasks = relationship("Task", back_populates="module")
    dependencies = relationship(
        "ModuleDependency",
        foreign_keys="ModuleDependency.module_id",
        back_populates="module",
        cascade="all, delete-orphan",
    )
    depended_by = relationship(
        "ModuleDependency",
        foreign_keys="ModuleDependency.depends_on_module_id",
        back_populates="depends_on_module",
        cascade="all, delete-orphan",
    )


class ModuleDependency(Base):
    __tablename__ = "module_dependencies"

    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    depends_on_module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("module_id", "depends_on_module_id", name="uq_module_dep"),
    )

    module = relationship("Module", foreign_keys=[module_id], back_populates="dependencies")
    depends_on_module = relationship("Module", foreign_keys=[depends_on_module_id], back_populates="depended_by")
