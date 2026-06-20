from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LifeBlock(BaseModel):
    __tablename__ = "life_blocks"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String(100), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    status = Column(String(20), default="ACTIVE")

    user = relationship("User", back_populates="life_blocks")
    days = relationship("LifeBlockDay", back_populates="life_block")


class LifeBlockDay(BaseModel):
    __tablename__ = "life_block_days"

    life_block_id = Column(Integer, ForeignKey("life_blocks.id"), nullable=False)
    day = Column(String(3), nullable=False)

    life_block = relationship("LifeBlock", back_populates="days")


class WeekSchedule(BaseModel):
    __tablename__ = "week_schedules"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_of = Column(Date, nullable=False)
    status = Column(String(20), default="DRAFT")
    locked_at = Column(DateTime)
    summary_line = Column(String(500))

    blocks = relationship("ScheduleBlock", back_populates="week_schedule")


class ScheduleBlock(BaseModel):
    __tablename__ = "schedule_blocks"

    week_schedule_id = Column(Integer, ForeignKey("week_schedules.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    goal_id = Column(Integer, ForeignKey("goals.id"))
    life_block_id = Column(Integer, ForeignKey("life_blocks.id"))
    type = Column(String(20), nullable=False)
    day = Column(String(3), nullable=False)
    block_date = Column(Date)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    label = Column(String(200), nullable=False)
    task_description = Column(String(500))
    output_definition = Column(String(500))
    status = Column(String(20), default="SCHEDULED")
    moved_to_block_id = Column(Integer, ForeignKey("schedule_blocks.id"))

    week_schedule = relationship("WeekSchedule", back_populates="blocks")
