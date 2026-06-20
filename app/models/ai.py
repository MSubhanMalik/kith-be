from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text

from app.models.base import BaseModel


class AIRun(BaseModel):
    __tablename__ = "ai_runs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    run_type = Column(String(30), nullable=False)
    entity_type = Column(String(20))
    entity_id = Column(Integer)
    status = Column(String(20), default="QUEUED")
    input_payload = Column(Text)
    output_payload = Column(Text)
    error_message = Column(Text)
    model = Column(String(50))
    tokens_used = Column(Integer)
    duration_ms = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ai_run_id = Column(Integer, ForeignKey("ai_runs.id"))
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(Text)
