from sqlalchemy import Column, String, Integer, Boolean, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Goal(BaseModel):
    __tablename__ = "goals"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String(500), nullable=False)
    target_date = Column(Date)
    current_status = Column(String(500))
    success_metric = Column(String(500))
    color_id = Column(String(20), nullable=False)
    rank = Column(Integer, nullable=False, default=1)
    weekly_hours = Column(Numeric(4, 1), nullable=False, default=0)
    is_private = Column(Boolean, default=False)
    nickname = Column(String(100))
    status = Column(String(20), default="ACTIVE")

    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal")
    notes = relationship("Note", back_populates="goal")


class Task(BaseModel):
    __tablename__ = "tasks"

    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String(500), nullable=False)
    description = Column(Text)
    output = Column(String(500))
    estimated_minutes = Column(Integer)
    week_number = Column(Integer)
    day_of_week = Column(String(3))
    scheduled_time = Column(String(5))
    status = Column(String(20), default="PENDING")
    sort_order = Column(Integer, default=0)
    is_auto_generated = Column(Boolean, default=False)

    goal = relationship("Goal", back_populates="tasks")


class Note(BaseModel):
    __tablename__ = "notes"

    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="ACTIVE")

    goal = relationship("Goal", back_populates="notes")
