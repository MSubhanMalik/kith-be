import json
import time as timer
from datetime import datetime

from sqlalchemy import select

from app.models import AIRun, Goal
from app.config import settings
from app.services.llm import LLMClient
from app.services.task import TaskService
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

    async def break_goal_into_tasks(self, goal_id: int):
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == self.user.id, Goal.status != "DELETED")
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return []

        if not settings.OPENROUTER_API_KEY:
            return []

        ai_run = await self.run("GOAL_BREAKDOWN", json.dumps({"goal_id": goal_id, "label": goal.label}), "GOAL", goal_id)
        start = timer.time()

        prompt = f"""Break this goal into concrete, actionable tasks for a weekly schedule.

Goal: {goal.label}
Target date: {goal.target_date or "No deadline set"}
Weekly hours available: {float(goal.weekly_hours or 0)}h
Current status: {goal.current_status or "Just starting"}

Rules:
- Each task should be completable in a single sitting (30-180 minutes)
- Include a time estimate in minutes for each task
- Assign each task a day of the week (Mon, Tue, Wed, Thu, Fri, Sat)
- Spread tasks across the week, not all on one day
- Order tasks by what should be done first
- Be specific: "Build user auth with JWT" not "Work on backend"
- Include an output definition: what does "done" look like
- Generate 5-12 tasks depending on complexity

Return a JSON object with a "tasks" key containing an array:
{{"tasks": [{{"text": "...", "description": "...", "output": "...", "estimatedMinutes": 60, "dayOfWeek": "Mon"}}]}}"""

        llm = LLMClient()
        try:
            response = await llm.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a project planning assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.OPENROUTER_MODEL_SMART,
                response_format={"type": "json_object"},
                temperature=0.5,
            )

            content = response.choices[0].message.content
            tasks_data = json.loads(content)
            if isinstance(tasks_data, dict):
                tasks_data = tasks_data.get("tasks", [])

            task_service = TaskService(self.ctx)
            created = []
            for t in tasks_data:
                task_result = await task_service.create_task(goal_id, {
                    "text": t.get("text", "Unnamed task"),
                    "description": t.get("description"),
                    "output": t.get("output"),
                    "estimated_minutes": t.get("estimatedMinutes", 60),
                    "day_of_week": t.get("dayOfWeek"),
                    "is_auto_generated": True,
                })
                created.append(task_result)

            tokens = response.usage.total_tokens if response.usage else 0
            duration_ms = int((timer.time() - start) * 1000)
            await self.complete_run(ai_run.id, json.dumps(created, default=str), tokens, duration_ms)
            return created

        except Exception as e:
            await self.fail_run(ai_run.id, str(e))
            return []

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
