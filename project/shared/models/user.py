from shared.models.base import Base, UUID
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime(timezone=True))

    projects = relationship("Project", back_populates="created_by_user")
    api_keys = relationship("ApiKey", back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(20), nullable=False)
    permissions = Column(JSON, default=lambda: ["read"])
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="api_keys")
