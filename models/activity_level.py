from uuid import uuid4

from sqlalchemy import UUID, Column, Integer, ForeignKey, String, Enum
from sqlalchemy.orm import relationship

from db.session import Base


activity_levels = ("Inactive", "Moderately active", "Active")

class UserActivityLevel(Base):

    __tablename__ = "user_activity_level"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True, index=True)
    date = Column(Integer, nullable=False)
    level = Column(Enum(*activity_levels, name="activity_level_enum"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)