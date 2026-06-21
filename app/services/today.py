from datetime import datetime, date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import DayLog, TaskCompletion, WeekSchedule, ScheduleBlock
from app.utils import get_error


class TodayService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def get_today(self, target_date: date = None):
        today = target_date or date.today()
        day_name = today.strftime("%a").upper()[:3]

        day_log = await self._get_or_create_log(today)

        completions_result = await self.db.execute(
            select(TaskCompletion).where(TaskCompletion.day_log_id == day_log.id)
        )
        completions = {
            tc.schedule_block_id: tc.status
            for tc in completions_result.scalars().all()
        }

        monday = today - timedelta(days=today.weekday())
        week_result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == monday)
        )
        schedule = week_result.scalar_one_or_none()

        blocks = []
        if schedule:
            for b in schedule.blocks:
                if b.day == day_name:
                    blocks.append({
                        "id": b.id,
                        "type": b.type,
                        "day": b.day,
                        "blockDate": str(b.block_date) if b.block_date else str(today),
                        "time": {"start": b.start_time, "end": b.end_time},
                        "label": b.label,
                        "taskDescription": b.task_description or "",
                        "outputDefinition": b.output_definition or "",
                        "taskId": b.task_id,
                        "goalId": b.goal_id,
                        "status": completions.get(b.id, b.status),
                    })
            blocks.sort(key=lambda x: x["time"]["start"])

        return {
            "date": str(today),
            "dayLog": self._log_to_dict(day_log),
            "blocks": blocks,
            "completions": completions,
        }

    async def complete_block(self, block_id: int, status: str):
        result = await self.db.execute(
            select(ScheduleBlock)
            .join(WeekSchedule)
            .where(ScheduleBlock.id == block_id, WeekSchedule.user_id == self.user.id)
        )
        block = result.scalar_one_or_none()
        if not block:
            raise get_error("NOT_FOUND")

        today = date.today()
        day_log = await self._get_or_create_log(today)

        existing = await self.db.execute(
            select(TaskCompletion).where(
                TaskCompletion.day_log_id == day_log.id,
                TaskCompletion.schedule_block_id == block_id,
            )
        )
        completion = existing.scalar_one_or_none()

        if completion:
            completion.status = status
            completion.completed_at = datetime.utcnow() if status == "DONE" else None
        else:
            completion = TaskCompletion(
                day_log_id=day_log.id,
                schedule_block_id=block_id,
                status=status,
                completed_at=datetime.utcnow() if status == "DONE" else None,
            )
            self.db.add(completion)

        status_map = {"DONE": "COMPLETED", "MISSED": "SKIPPED", "PARTIAL": "ACTIVE", "PENDING": "SCHEDULED"}
        block.status = status_map.get(status, block.status)
        await self.db.commit()

        return {
            "blockId": block_id,
            "status": status,
            "completedAt": completion.completed_at.isoformat() if completion.completed_at else None,
        }

    async def close_day(self, target_date: date = None):
        today = target_date or date.today()
        day_log = await self._get_or_create_log(today)

        if day_log.night_done_at:
            return self._log_to_dict(day_log)

        day_log.night_done_at = datetime.utcnow()
        await self.db.commit()
        return self._log_to_dict(day_log)

    async def _get_or_create_log(self, target_date: date):
        result = await self.db.execute(
            select(DayLog).where(DayLog.user_id == self.user.id, DayLog.date == target_date)
        )
        log = result.scalar_one_or_none()
        if not log:
            log = DayLog(user_id=self.user.id, date=target_date)
            self.db.add(log)
            await self.db.flush()
        return log

    def _log_to_dict(self, log):
        return {
            "id": log.id,
            "date": str(log.date),
            "morningDoneAt": log.morning_done_at.isoformat() if log.morning_done_at else None,
            "nightDoneAt": log.night_done_at.isoformat() if log.night_done_at else None,
            "energyLevel": log.energy_level,
        }
