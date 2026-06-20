from datetime import datetime, date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import LifeBlock, LifeBlockDay, WeekSchedule, ScheduleBlock
from app.utils import get_error


class ScheduleService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def get_week(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None
        return self._week_to_dict(schedule)

    async def generate_schedule(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()

        existing = await self.db.execute(
            select(WeekSchedule).where(
                WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date
            )
        )
        if existing.scalar_one_or_none():
            raise get_error("DUPLICATE_ENTRY")

        schedule = WeekSchedule(
            user_id=self.user.id,
            week_of=week_date,
            status="DRAFT",
        )
        self.db.add(schedule)
        await self.db.flush()

        life_blocks_result = await self.db.execute(
            select(LifeBlock)
            .options(selectinload(LifeBlock.days))
            .where(LifeBlock.user_id == self.user.id, LifeBlock.status == "ACTIVE")
        )
        life_blocks = life_blocks_result.scalars().all()

        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

        for lb in life_blocks:
            for lb_day in lb.days:
                day_offset = day_map.get(lb_day.day.lower(), 0)
                block_date = week_date + timedelta(days=day_offset)
                block = ScheduleBlock(
                    week_schedule_id=schedule.id,
                    life_block_id=lb.id,
                    type="LIFE_BLOCK",
                    day=lb_day.day.upper()[:3],
                    block_date=block_date,
                    start_time=lb.start_time,
                    end_time=lb.end_time,
                    label=lb.label,
                    status="SCHEDULED",
                )
                self.db.add(block)

        await self.db.commit()

        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.id == schedule.id)
        )
        return self._week_to_dict(result.scalar_one())

    async def lock_week(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule).where(
                WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise get_error("NOT_FOUND")
        if schedule.status == "LOCKED":
            raise get_error("SCHEDULE_LOCKED")

        schedule.status = "LOCKED"
        schedule.locked_at = datetime.utcnow()
        await self.db.commit()

        full = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.id == schedule.id)
        )
        return self._week_to_dict(full.scalar_one())

    async def reschedule_week(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise get_error("NOT_FOUND")

        return self._week_to_dict(schedule)

    async def move_block(self, block_id: int, new_day: str, new_time: str):
        result = await self.db.execute(
            select(ScheduleBlock)
            .join(WeekSchedule)
            .where(ScheduleBlock.id == block_id, WeekSchedule.user_id == self.user.id)
        )
        block = result.scalar_one_or_none()
        if not block:
            raise get_error("NOT_FOUND")

        block.day = new_day
        block.start_time = new_time
        block.status = "SCHEDULED"
        await self.db.commit()
        return self._schedule_block_to_dict(block)

    async def update_summary(self, week_of: str, summary_line: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule).where(
                WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise get_error("NOT_FOUND")
        schedule.summary_line = summary_line
        await self.db.commit()

    async def list_life_blocks(self):
        result = await self.db.execute(
            select(LifeBlock)
            .options(selectinload(LifeBlock.days))
            .where(LifeBlock.user_id == self.user.id, LifeBlock.status == "ACTIVE")
        )
        return [self._life_block_to_dict(b) for b in result.scalars().all()]

    async def create_life_block(self, data: dict):
        block = LifeBlock(
            user_id=self.user.id,
            label=data["label"],
            start_time=data["start_time"],
            end_time=data["end_time"],
        )
        self.db.add(block)
        await self.db.flush()

        for day in data.get("days", []):
            self.db.add(LifeBlockDay(life_block_id=block.id, day=day))

        await self.db.commit()

        result = await self.db.execute(
            select(LifeBlock)
            .options(selectinload(LifeBlock.days))
            .where(LifeBlock.id == block.id)
        )
        return self._life_block_to_dict(result.scalar_one())

    async def update_life_block(self, block_id: int, data: dict):
        block = await self._get_life_block_or_404(block_id)

        if "label" in data and data["label"] is not None:
            block.label = data["label"]
        if "start_time" in data and data["start_time"] is not None:
            block.start_time = data["start_time"]
        if "end_time" in data and data["end_time"] is not None:
            block.end_time = data["end_time"]

        if "days" in data and data["days"] is not None:
            existing = await self.db.execute(
                select(LifeBlockDay).where(LifeBlockDay.life_block_id == block_id)
            )
            for row in existing.scalars().all():
                await self.db.delete(row)

            for day in data["days"]:
                self.db.add(LifeBlockDay(life_block_id=block_id, day=day))

        await self.db.commit()

        result = await self.db.execute(
            select(LifeBlock)
            .options(selectinload(LifeBlock.days))
            .where(LifeBlock.id == block_id)
        )
        return self._life_block_to_dict(result.scalar_one())

    async def delete_life_block(self, block_id: int):
        block = await self._get_life_block_or_404(block_id)
        block.status = "DELETED"
        await self.db.commit()

    async def _get_life_block_or_404(self, block_id: int):
        result = await self.db.execute(
            select(LifeBlock).where(
                LifeBlock.id == block_id, LifeBlock.user_id == self.user.id, LifeBlock.status == "ACTIVE"
            )
        )
        block = result.scalar_one_or_none()
        if not block:
            raise get_error("NOT_FOUND")
        return block

    def _week_to_dict(self, schedule):
        return {
            "id": schedule.id,
            "weekOf": str(schedule.week_of),
            "status": schedule.status,
            "lockedAt": schedule.locked_at.isoformat() if schedule.locked_at else None,
            "summaryLine": schedule.summary_line or "",
            "blocks": [self._schedule_block_to_dict(b) for b in schedule.blocks],
            "createdAt": schedule.created_at.isoformat() if schedule.created_at else None,
            "updatedAt": schedule.updated_at.isoformat() if schedule.updated_at else None,
        }

    def _schedule_block_to_dict(self, block):
        return {
            "id": block.id,
            "type": block.type,
            "day": block.day,
            "blockDate": str(block.block_date) if block.block_date else None,
            "time": {
                "start": block.start_time,
                "end": block.end_time,
            },
            "label": block.label,
            "taskDescription": block.task_description or "",
            "outputDefinition": block.output_definition or "",
            "taskId": block.task_id,
            "goalId": block.goal_id,
            "lifeBlockId": block.life_block_id,
            "status": block.status,
            "movedToBlockId": block.moved_to_block_id,
        }

    def _life_block_to_dict(self, block):
        return {
            "id": block.id,
            "label": block.label,
            "time": {
                "start": block.start_time,
                "end": block.end_time,
            },
            "days": [d.day for d in block.days],
            "createdAt": block.created_at.isoformat() if block.created_at else None,
            "updatedAt": block.updated_at.isoformat() if block.updated_at else None,
        }
