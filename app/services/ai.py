import asyncio
import json
import traceback
import time as timer
from datetime import datetime

from sqlalchemy import select

from app.models import AIRun, Goal
from app.config import settings
from app.services.llm import LLMClient
from app.services.nudge import NudgeService
from app.services.context_builder import ContextBuilder


class AIService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()
        self.ctx = ctx

    async def run(self, run_type: str, input_payload: str, entity_type: str = None, entity_id: int = None):
        ai_run = AIRun(
            user_id=self.user.id,
            run_type=run_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status="QUEUED",
            input_payload=input_payload,
            model=settings.OPENROUTER_MODEL_SMART,
            started_at=datetime.utcnow(),
        )
        self.db.add(ai_run)
        await self.db.flush()
        await self.db.commit()
        return ai_run

    async def complete_run(self, run_id: int, output_payload: str, tokens_used: int = 0, duration_ms: int = 0):
        result = await self.db.execute(select(AIRun).where(AIRun.id == run_id))
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
        result = await self.db.execute(select(AIRun).where(AIRun.id == run_id))
        ai_run = result.scalar_one_or_none()
        if not ai_run:
            return
        ai_run.status = "FAILED"
        ai_run.error_message = error_message
        ai_run.completed_at = datetime.utcnow()
        await self.db.commit()

    async def start_goal_breakdown(self, goal_id: int) -> dict:
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == self.user.id, Goal.status != "DELETED")
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return {"error": "Goal not found"}

        if not settings.OPENROUTER_API_KEY:
            return {"error": "No API key configured"}

        ai_run = await self.run("GOAL_BREAKDOWN", json.dumps({"goal_id": goal_id, "label": goal.label}), "GOAL", goal_id)

        asyncio.create_task(_run_goal_breakdown(
            user_id=self.user.id,
            goal_id=goal_id,
            ai_run_id=ai_run.id,
            goal_label=goal.label,
            goal_status=goal.current_status or "",
            goal_metric=goal.success_metric or "",
            goal_target_date=str(goal.target_date) if goal.target_date else None,
            goal_weekly_hours=float(goal.weekly_hours or 0),
        ))

        return {"ai_run_id": ai_run.id, "status": "processing"}

    async def break_goal_into_tasks(self, goal_id: int):
        return await self.start_goal_breakdown(goal_id)

    async def generate_cat_message(self, trigger: str = "on_demand"):
        if not settings.OPENROUTER_API_KEY:
            return {"message": "Set up an API key so I can think."}

        context_builder = ContextBuilder(self.ctx)
        context = await context_builder.build_chat_context()
        context_text = context_builder.format_for_prompt(context)

        prompt = f"""Generate a short nudge message (1-2 sentences) based on the user's current state.

Trigger: {trigger}
{context_text}

TONE: Smart friend with their calendar open. Data first, then a question. Never judgmental. No emojis.
EXAMPLES:
- "Freelancing is 3 hours behind this week. Want to swap tonight's LinkedIn slot?"
- "You finished 4 of 5 blocks today. One more and it's a clean sweep."
- "Thursday has 3 deep tasks back to back. Maybe spread one to Friday?"

Return only the message text. No quotes. No prefix."""

        llm = LLMClient()
        try:
            response = await llm.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are Kith, a cat productivity companion. Generate a single short nudge."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.OPENROUTER_MODEL_FAST,
                temperature=0.8,
                max_tokens=150,
            )

            message = response.choices[0].message.content.strip().strip('"')
            nudge_service = NudgeService(self.ctx)
            return await nudge_service.create_nudge(trigger, message)

        except Exception:
            return {"message": "Couldn't generate a nudge right now."}

    async def generate_weekly_summary(self, week_of: str):
        if not settings.OPENROUTER_API_KEY:
            return ""

        context_builder = ContextBuilder(self.ctx)
        context = await context_builder.build_chat_context()
        context_text = context_builder.format_for_prompt(context)

        prompt = f"""Generate a one-line weekly summary (under 80 characters) for this week.

{context_text}

Examples: "Shipped auth, 3 leads closed, LinkedIn behind" or "Slow week — sick 2 days, only freelancing got done"
Return only the summary line. No quotes."""

        llm = LLMClient()
        try:
            response = await llm.chat_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                model=settings.OPENROUTER_MODEL_FAST,
                temperature=0.5,
                max_tokens=50,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception:
            return ""


async def _run_goal_breakdown(
    user_id: int,
    goal_id: int,
    ai_run_id: int,
    goal_label: str,
    goal_status: str,
    goal_metric: str,
    goal_target_date: str | None,
    goal_weekly_hours: float,
):
    from app.db.database import async_session

    start = timer.time()

    async with async_session() as db:
        try:
            description = goal_status
            weeks_to_target = 4
            if goal_target_date:
                from datetime import date as dateclass
                days_left = (dateclass.fromisoformat(goal_target_date) - dateclass.today()).days
                weeks_to_target = max(1, min(16, days_left // 7))

            import re
            week_match = re.search(r'(\d+)[\s-]*(?:to\s*\d+\s*)?weeks?', description.lower())
            if week_match:
                weeks_to_target = int(week_match.group(1))
            success = goal_metric

            prompt = f"""Extract a concrete daily task schedule from the user's goal and description. Follow the user's plan exactly — do not invent your own structure. If the user described a specific order or curriculum, follow it faithfully.

Goal: {goal_label}
{f"User's description and plan: {description}" if description else ""}
{f"Success looks like: {success}" if success else ""}
Target date: {goal_target_date or "No deadline set"}
Weeks available: {weeks_to_target}
Weekly hours available: {goal_weekly_hours}h

Rules:
- Span exactly {weeks_to_target} weeks
- Use ALL 7 days per week: Mon, Tue, Wed, Thu, Fri, Sat, Sun — unless the user says otherwise
- Each day should have 1-2 tasks
- Each task: one focused session (30-120 minutes)
- Assign each task a start time in HH:MM format. Spread across the day.
- Follow the user's described sequence exactly. If they said "first HTML, then CSS, then JS", do that order.
- Match the user's pace. If they said "beginner" or "take it slow", make early tasks small and simple.
- Task text should be a concrete action, not a topic. "Build chess board with HTML table" not "Learn HTML".
- Output = what proves this task is done.
- If the user described specific sub-steps, turn each sub-step into its own task on its own day.

Return JSON:
{{"tasks": [{{"text": "...", "description": "...", "output": "...", "estimatedMinutes": 60, "dayOfWeek": "Mon", "weekNumber": 1, "scheduledTime": "09:00"}}]}}"""

            llm = LLMClient()
            response = await llm.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a project planning assistant. Return ONLY a valid JSON object, no markdown, no explanation. Keep task text under 12 words. Keep descriptions under 25 words."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.OPENROUTER_MODEL_SMART,
                temperature=0.3,
                max_tokens=8192,
            )

            content = response.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3].strip()

            tasks_data = json.loads(content)
            if isinstance(tasks_data, dict):
                tasks_data = tasks_data.get("tasks", [])

            from app.services.task import TaskService

            class BgContext:
                def __init__(self, db, user_id):
                    self.db = db
                    self._user_id = user_id
                def require_user(self):
                    class FakeUser:
                        id = self._user_id
                    return FakeUser()

            bg_ctx = BgContext(db, user_id)
            task_service = TaskService(bg_ctx)
            created = []
            for t in tasks_data:
                task_result = await task_service.create_task(goal_id, {
                    "text": t.get("text", "Unnamed task"),
                    "description": t.get("description"),
                    "output": t.get("output"),
                    "estimated_minutes": t.get("estimatedMinutes", 60),
                    "day_of_week": t.get("dayOfWeek"),
                    "scheduled_time": t.get("scheduledTime"),
                    "week_number": t.get("weekNumber", 1),
                    "is_auto_generated": True,
                })
                created.append(task_result)

            tokens = response.usage.total_tokens if response.usage else 0
            duration_ms = int((timer.time() - start) * 1000)

            result = await db.execute(select(AIRun).where(AIRun.id == ai_run_id))
            ai_run = result.scalar_one_or_none()
            if ai_run:
                ai_run.status = "COMPLETED"
                ai_run.output_payload = json.dumps(created, default=str)
                ai_run.tokens_used = tokens
                ai_run.duration_ms = duration_ms
                ai_run.completed_at = datetime.utcnow()
                await db.commit()

        except Exception as e:
            traceback.print_exc()
            try:
                result = await db.execute(select(AIRun).where(AIRun.id == ai_run_id))
                ai_run = result.scalar_one_or_none()
                if ai_run:
                    ai_run.status = "FAILED"
                    ai_run.error_message = str(e)
                    ai_run.completed_at = datetime.utcnow()
                    await db.commit()
            except Exception:
                traceback.print_exc()
