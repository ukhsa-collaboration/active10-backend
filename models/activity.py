from uuid import uuid4

from sqlalchemy import (
    Integer,
    Column,
    ForeignKey,
    UUID,
    JSON,
    String,
    BigInteger,
    ARRAY,
)

from db.session import Base


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = {"postgresql_partition_by": "RANGE (date)"}

    id = Column(UUID(as_uuid=True), default=uuid4, primary_key=True, index=True)
    date = Column(BigInteger, nullable=False, primary_key=True, index=True)
    user_postcode = Column(String(10), nullable=False)
    user_age_range = Column(String(50), nullable=False)
    brisk_minutes = Column(Integer, nullable=False)
    walking_minutes = Column(Integer, nullable=False)
    steps = Column(Integer, nullable=False)
    rewards = Column(ARRAY(JSON), nullable=True)

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
