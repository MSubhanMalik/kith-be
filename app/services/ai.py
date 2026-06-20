from datetime import datetime

from sqlalchemy import select

from app.models import AIRun
from app.config import settings


class AIService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def run(self, run_type: str, input_payload: str, entity_type: str = None, entity_id: int = None):
        ai_run = AIRun(
            user_id=self.user.id,
            run_type=run_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status="QUEUED",
            input_payload=input_payload,
            model=settings.OPENROUTER_SMART_MODEL,
            started_at=datetime.utcnow(),
        )
        self.db.add(ai_run)
        await self.db.flush()
        await self.db.commit()
        return ai_run

    async def complete_run(self, run_id: int, output_payload: str, tokens_used: int = 0, duration_ms: int = 0):
        result = await self.db.execute(
            select(AIRun).where(AIRun.id == run_id)
        )
        ai_run = result.scalar_one_or_none()
        if not ai_run:
            return

        ai_run.status = "COMPLETED"
        ai_run.output_payload = output_payload
        ai_run.tokens_used = tokens_used
        ai_run.duration_ms = duration_ms
        ai_run.completed_at = datetime.utcnow()
        await self.db.commit()

    async def fail_run(self, run_id: int, error_message: str):
        result = await self.db.execute(
            select(AIRun).where(AIRun.id == run_id)
        )
        ai_run = result.scalar_one_or_none()
        if not ai_run:
            return

        ai_run.status = "FAILED"
        ai_run.error_message = error_message
        ai_run.completed_at = datetime.utcnow()
        await self.db.commit()

    async def break_goal_into_tasks(self, goal_id: int):
        pass

    async def generate_cat_message(self, context: dict):
        pass

    async def suggest_reschedule(self, week_of: str):
        pass

    async def generate_weekly_summary(self, week_of: str):
        pass
