from datetime import datetime
from uuid import uuid4
from enum import Enum
from sqlalchemy import Column, Date, String, UUID, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from db.session import Base


class UserStatus(str, Enum):
    LOGIN = "Login"
    LOGOUT = "Logout"


class UserDeleteReason(str, Enum):
    DISCONNECTED = "Disconnected"
    LOGOUT_DELETED_AFTER_365_DAYS = "Logout deleted after 365 days"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True, index=True)
    unique_id = Column(String(length=50), unique=True, index=True, nullable=False)
    nhs_number = Column(String(length=10), nullable=False)
    first_name = Column(String(length=50), nullable=False)
    email = Column(String(length=254))
    date_of_birth = Column(Date)
    gender = Column(String(length=6), nullable=False, default="")
    postcode = Column(String(length=10), nullable=True, default="")
    identity_level = Column(String(length=2), nullable=False)
    status = Column(String(length=10), nullable=True, default=UserStatus.LOGIN.value)
    status_updated_at = Column(DateTime, nullable=True, default=datetime.utcnow())

    token = relationship("UserToken", back_populates="user", uselist=False, cascade="all, delete")
    email_preferences = relationship("EmailPreference", backref="users", uselist=True, cascade="all, delete")

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    token = Column(String(length=500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    user = relationship("User", back_populates="token")


class DeleteAudit(Base):
    __tablename__ = "delete_audit"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    delete_reason = Column(String(length=50), nullable=False)
    deleted_at = Column(DateTime, nullable=False, default=datetime.utcnow())


class EmailPreference(Base):
    __tablename__ = "email_preferences"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(length=200), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
