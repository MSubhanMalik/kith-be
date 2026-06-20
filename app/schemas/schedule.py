from typing import Optional, List
from pydantic import BaseModel


class CreateLifeBlockRequest(BaseModel):
    label: str
    start_time: str
    end_time: str
    days: List[str]


class UpdateLifeBlockRequest(BaseModel):
    label: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days: Optional[List[str]] = None


class GenerateScheduleRequest(BaseModel):
    week_of: str


class MoveTaskRequest(BaseModel):
    new_day: str
    new_time: str


class ChatMessageRequest(BaseModel):
    message: str
