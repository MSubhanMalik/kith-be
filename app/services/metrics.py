from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import WeekMetric, GoalWeekMetric, WeekSchedule, ScheduleBlock, DayLog, TaskCompletion


class MetricsService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def get_week_metrics(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekMetric)
            .options(selectinload(WeekMetric.goal_metrics))
            .where(WeekMetric.user_id == self.user.id, WeekMetric.week_of == week_date)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            return None
        return self._to_dict(metric)

    async def compute_week_metrics(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()

        schedule_result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date)
        )
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            return None

        goal_blocks = [b for b in schedule.blocks if b.type == "GOAL_TASK"]
        total_planned = len(goal_blocks)
        total_done = sum(1 for b in goal_blocks if b.status == "COMPLETED")

        existing = await self.db.execute(
            select(WeekMetric).where(
                WeekMetric.user_id == self.user.id, WeekMetric.week_of == week_date
            )
        )
        metric = existing.scalar_one_or_none()

        if metric:
            metric.total_tasks_planned = total_planned
            metric.total_tasks_done = total_done
        else:
            metric = WeekMetric(
                user_id=self.user.id,
                week_of=week_date,
                total_tasks_planned=total_planned,
                total_tasks_done=total_done,
            )
            self.db.add(metric)

        await self.db.flush()
        await self.db.commit()

        full = await self.db.execute(
            select(WeekMetric)
            .options(selectinload(WeekMetric.goal_metrics))
            .where(WeekMetric.id == metric.id)
        )
        return self._to_dict(full.scalar_one())

    def _to_dict(self, metric):
        return {
            "id": metric.id,
            "weekOf": str(metric.week_of),
            "totalTasksPlanned": metric.total_tasks_planned,
            "totalTasksDone": metric.total_tasks_done,
            "totalHoursPlanned": float(metric.total_hours_planned) if metric.total_hours_planned else 0,
            "totalHoursCompleted": float(metric.total_hours_completed) if metric.total_hours_completed else 0,
            "avgEnergy": float(metric.avg_energy) if metric.avg_energy else None,
            "patterns": metric.patterns,
            "goalMetrics": [
                {
                    "goalId": gm.goal_id,
                    "hoursPlanned": float(gm.hours_planned) if gm.hours_planned else 0,
                    "hoursCompleted": float(gm.hours_completed) if gm.hours_completed else 0,
                    "tasksDone": gm.tasks_done,
                    "tasksTotal": gm.tasks_total,
                    "status": gm.status,
                }
                for gm in metric.goal_metrics
            ],
        }
