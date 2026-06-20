from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import WeekSchedule, Goal, Task, Export
from app.utils import get_error


class ExportService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def export_week(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise get_error("NOT_FOUND")

        export = Export(
            user_id=self.user.id,
            type="WEEKLY_SCHEDULE",
            entity_id=schedule.id,
            filename=f"kith-week-{week_of}.xlsx",
        )
        self.db.add(export)
        await self.db.commit()

        blocks = []
        for b in schedule.blocks:
            blocks.append({
                "day": b.day,
                "startTime": b.start_time,
                "endTime": b.end_time,
                "label": b.label,
                "type": b.type,
                "status": b.status,
            })

        return {
            "weekOf": str(schedule.week_of),
            "blocks": sorted(blocks, key=lambda x: (x["day"], x["startTime"])),
            "filename": export.filename,
        }

    async def export_goal(self, goal_id: int):
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == self.user.id, Goal.status != "DELETED")
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise get_error("NOT_FOUND")

        tasks_result = await self.db.execute(
            select(Task)
            .where(Task.goal_id == goal_id, Task.user_id == self.user.id, Task.status != "DELETED")
            .order_by(Task.sort_order)
        )
        tasks = tasks_result.scalars().all()

        export = Export(
            user_id=self.user.id,
            type="GOAL_PLAN",
            entity_id=goal_id,
            filename=f"kith-goal-{goal.label[:30].replace(' ', '-').lower()}.xlsx",
        )
        self.db.add(export)
        await self.db.commit()

        return {
            "goal": {
                "id": goal.id,
                "label": goal.label,
                "targetDate": str(goal.target_date) if goal.target_date else None,
                "weeklyHours": float(goal.weekly_hours) if goal.weekly_hours else 0,
            },
            "tasks": [
                {
                    "text": t.text,
                    "description": t.description or "",
                    "output": t.output or "",
                    "dayOfWeek": t.day_of_week,
                    "status": t.status,
                }
                for t in tasks
            ],
            "filename": export.filename,
        }
