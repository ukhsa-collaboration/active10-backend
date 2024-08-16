from sqlalchemy import Integer, Column, ForeignKey, DATE, UUID

from db.session import Base


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    mins_brisk = Column(Integer)
    mins_walking = Column(Integer)
    steps = Column(Integer)
    activity_date = Column(DATE)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
