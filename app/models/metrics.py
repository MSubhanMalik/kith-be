from sqlalchemy import Column, String, Integer, Date, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class WeekMetric(BaseModel):
    __tablename__ = "week_metrics"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_of = Column(Date, nullable=False)
    total_tasks_planned = Column(Integer, default=0)
    total_tasks_done = Column(Integer, default=0)
    total_hours_planned = Column(Numeric(5, 1), default=0)
    total_hours_completed = Column(Numeric(5, 1), default=0)
    avg_energy = Column(Numeric(3, 1))
    patterns = Column(Text)

    goal_metrics = relationship("GoalWeekMetric", back_populates="week_metric")


class GoalWeekMetric(BaseModel):
    __tablename__ = "goal_week_metrics"

    week_metric_id = Column(Integer, ForeignKey("week_metrics.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    hours_planned = Column(Numeric(4, 1), default=0)
    hours_completed = Column(Numeric(4, 1), default=0)
    tasks_done = Column(Integer, default=0)
    tasks_total = Column(Integer, default=0)
    status = Column(String(20))

    week_metric = relationship("WeekMetric", back_populates="goal_metrics")
