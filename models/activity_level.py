from uuid import uuid4

from sqlalchemy import UUID, Column, Integer, ForeignKey, String

from db.session import Base


class UserActivityLevel(Base):
    __tablename__ = "user_activity_level"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True, index=True)
    level = Column(String(length=50))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)
