from sqlalchemy import Column, String, Integer, ForeignKey, Text

from app.models.base import BaseModel


class ActivityLog(BaseModel):
    __tablename__ = "activity_log"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(Integer)
    action = Column(String(50), nullable=False)
    payload = Column(Text)


class Export(BaseModel):
    __tablename__ = "exports"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), nullable=False)
    entity_id = Column(Integer)
    filename = Column(String(255))
