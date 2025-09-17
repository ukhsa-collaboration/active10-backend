from uuid import uuid4

from sqlalchemy import JSON, UUID, Column, ForeignKey

from db.session import Base


class UserWalkingPlan(Base):
    __tablename__ = "user_walking_plan"

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True, index=True)
    walking_plan_data = Column(JSON, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
