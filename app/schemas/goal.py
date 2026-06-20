from typing import Optional, List
from pydantic import BaseModel


class CreateGoalRequest(BaseModel):
    label: str
    target_date: Optional[str] = None
    weekly_hours: float = 0
    is_private: bool = False
    nickname: Optional[str] = None


class UpdateGoalRequest(BaseModel):
    label: Optional[str] = None
    target_date: Optional[str] = None
    current_status: Optional[str] = None
    success_metric: Optional[str] = None
    weekly_hours: Optional[float] = None
    rank: Optional[int] = None
    is_private: Optional[bool] = None
    nickname: Optional[str] = None
    status: Optional[str] = None


class ReorderGoalsRequest(BaseModel):
    ordered_ids: List[int]


class CreateTaskRequest(BaseModel):
    text: str
    description: Optional[str] = None
    output: Optional[str] = None
    day_of_week: Optional[str] = None
    scheduled_time: Optional[str] = None
    estimated_minutes: Optional[int] = None


class UpdateTaskRequest(BaseModel):
    text: Optional[str] = None
    description: Optional[str] = None
    output: Optional[str] = None
    day_of_week: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
