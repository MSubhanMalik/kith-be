from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey

from app.models.base import BaseModel


class Nudge(BaseModel):
    __tablename__ = "nudges"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_block_id = Column(Integer, ForeignKey("schedule_blocks.id"))
    type = Column(String(30), nullable=False)
    message = Column(String(500), nullable=False)
    dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime)
