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

        weeks_to_target = 4
        if goal.target_date:
            from datetime import date as dateclass
            days_left = (goal.target_date - dateclass.today()).days
            weeks_to_target = max(1, min(12, days_left // 7))

        description = goal.current_status or ""
        success = goal.success_metric or ""

        prompt = f"""Create a multi-week plan to achieve this goal. Break it into weekly milestones, then into daily tasks.

Goal: {goal.label}
{f"Description: {description}" if description else ""}
{f"Success looks like: {success}" if success else ""}
Target date: {goal.target_date or "No deadline set"}
Weeks available: {weeks_to_target}
Weekly hours available: {float(goal.weekly_hours or 0)}h

Rules:
- Create a plan spanning {min(weeks_to_target, 6)} weeks
- Each week should have 3-6 tasks that build toward the goal
- Tasks in week 1 are foundations, later weeks build on earlier work
- Each task: completable in one sitting (30-120 minutes)
- Assign each task a day (Mon, Tue, Wed, Thu, Fri, Sat) — spread across the week
- Assign each task a start time in HH:MM 24-hour format (e.g. "09:00", "14:30"). Spread tasks throughout the day, don't stack them all at the same time.
- Be specific and actionable: "Read chapter 1 of [topic]" not "Study"
- Include what "done" looks like for each task
- Earlier weeks = learning/setup, later weeks = building/executing

Return JSON:
{{"tasks": [{{"text": "...", "description": "...", "output": "...", "estimatedMinutes": 60, "dayOfWeek": "Mon", "weekNumber": 1, "scheduledTime": "09:00"}}]}}"""

        llm = LLMClient()
        try:
            response = await llm.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a project planning assistant. Return ONLY a JSON object, no other text. Keep task text under 10 words. Keep descriptions under 20 words. Be concise."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.OPENROUTER_MODEL_SMART,
                temperature=0.5,
                max_tokens=4096,
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

            task_service = TaskService(self.ctx)
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
