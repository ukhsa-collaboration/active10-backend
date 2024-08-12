from uuid import uuid4

from sqlalchemy import Column, Date, String, UUID
from sqlalchemy.orm import relationship

from db.session import Base


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
    active = relationship("Activity", backref="user")
