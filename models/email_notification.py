from datetime import datetime, timezone
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import UUID, Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLAlchemyEnum

from db.session import Base


class LogoutNotificationType(PyEnum):
    LOGOUT_FOR_6_MONTHS = "Logged Out for 6 Months"
    LOGOUT_FOR_9_MONTHS = "Logged Out for 9 Months"
    LOGOUT_FOR_51_WEEKS = "Logged Out for 51 Weeks"
    LOGOUT_FOR_1_YEAR = "Logged Out for 1 Year"

    @classmethod
    def value_choices(cls):
        return [e.value for e in cls]


class EmailStatusEnum(PyEnum):
    SENT = "Sent"
    FAILED = "Failed"

    @classmethod
    def value_choices(cls):
        return [e.value for e in cls]


class LogoutUserEmailLogs(Base):
    __tablename__ = "logout_user_email_logs"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_email = Column(String(length=254), nullable=False, index=True)
    notification_type = Column(
        SQLAlchemyEnum(*LogoutNotificationType.value_choices(), name="notification_type_enum"),
        nullable=False,
        index=True,
    )
    email_delivery_status = Column(
        SQLAlchemyEnum(*EmailStatusEnum.value_choices(), name="email_status_enum"),
        nullable=False,
        index=True,
    )
    failure_reason = Column(String(length=128), nullable=True)
    message_id = Column(String(length=128), nullable=True)
    timestamp = Column(Integer, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=False), nullable=False, default=datetime.now(timezone.utc)  # noqa: UP017
    )  
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        default=datetime.now(timezone.utc),  # noqa: UP017
        onupdate=datetime.now(timezone.utc),  # noqa: UP017
    )


class MonthlyReportEmailLogs(Base):
    __tablename__ = "monthly_report_email_logs"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_email = Column(String(length=254), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    report_month = Column(String(length=12), nullable=False, index=True)
    email_delivery_status = Column(
        SQLAlchemyEnum(*EmailStatusEnum.value_choices(), name="report_email_status_enum"),
        nullable=False,
        index=True,
    )
    failure_reason = Column(String(length=128), nullable=True)
    message_id = Column(String(length=128), nullable=True)
    timestamp = Column(Integer, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=False), nullable=False, default=datetime.now(timezone.utc) # noqa: UP017
    )
    updated_at = Column(
        DateTime(timezone=False),
        nullable=False,
        default=datetime.now(timezone.utc),  # noqa: UP017
        onupdate=datetime.now(timezone.utc),  # noqa: UP017
    )
