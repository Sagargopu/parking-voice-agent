from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from .db import Base


class Intake(Base):
    __tablename__ = "intakes"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(64), unique=True, index=True, nullable=False)
    from_number = Column(String(32), index=True)
    name = Column(String(255))
    email = Column(String(255))
    issue_description = Column(Text)
    step = Column(String(32), default="name")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

