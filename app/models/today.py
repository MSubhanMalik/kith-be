from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class DayLog(BaseModel):
    __tablename__ = "day_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    morning_done_at = Column(DateTime)
    night_done_at = Column(DateTime)
    energy_level = Column(Integer)

    completions = relationship("TaskCompletion", back_populates="day_log")
    distractions = relationship("Distraction", back_populates="day_log")


class TaskCompletion(BaseModel):
    __tablename__ = "task_completions"

    day_log_id = Column(Integer, ForeignKey("day_logs.id"), nullable=False)
    schedule_block_id = Column(Integer, ForeignKey("schedule_blocks.id"), nullable=False)
    status = Column(String(20), nullable=False)
    completed_at = Column(DateTime)

    day_log = relationship("DayLog", back_populates="completions")


class Distraction(BaseModel):
    __tablename__ = "distractions"

    day_log_id = Column(Integer, ForeignKey("day_logs.id"), nullable=False)
    text = Column(String(500), nullable=False)

    day_log = relationship("DayLog", back_populates="distractions")
