from datetime import datetime, date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import LifeBlock, LifeBlockDay, WeekSchedule, ScheduleBlock, Goal, Task
from app.utils import get_error


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_time(m: int) -> str:
    m = m % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


class ScheduleService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def get_week(self, week_of: str, goal_id: int = None):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date)
        )
        schedule = result.scalars().first()
        if not schedule:
            return None
        return self._week_to_dict(schedule, goal_id=goal_id)

    async def generate_schedule(self, week_of: str):
        week_date = datetime.strptime(week_of, "%Y-%m-%d").date()

        existing_result = await self.db.execute(
            select(WeekSchedule).where(
                WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == week_date
            )
        )
        for existing in existing_result.scalars().all():
            from app.models import ScheduleBlock as SB
            await self.db.execute(
                SB.__table__.delete().where(SB.week_schedule_id == existing.id)
            )
            await self.db.delete(existing)
        await self.db.flush()

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

        life_blocks_by_day = {}
        for lb in life_blocks:
            for lb_day in lb.days:
                day_key = lb_day.day.upper()[:3]
                day_offset = day_map.get(lb_day.day.lower(), 0)
                block_date = week_date + timedelta(days=day_offset)
                block = ScheduleBlock(
                    week_schedule_id=schedule.id,
                    life_block_id=lb.id,
                    type="LIFE_BLOCK",
                    day=day_key,
                    block_date=block_date,
                    start_time=lb.start_time,
                    end_time=lb.end_time,
                    label=lb.label,
                    status="SCHEDULED",
                )
                self.db.add(block)
                life_blocks_by_day.setdefault(day_key, []).append((lb.start_time, lb.end_time))

        await self.db.flush()

        await self._place_goal_tasks(schedule, week_date, life_blocks_by_day, day_map)

        await self.db.commit()

        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.id == schedule.id)
        )
        return self._week_to_dict(result.scalar_one())

    async def _place_goal_tasks(self, schedule, week_date, life_blocks_by_day, day_map):
        free_slots = self._compute_free_slots(life_blocks_by_day)

        goals_result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == self.user.id, Goal.status == "ACTIVE")
            .order_by(Goal.rank)
        )
        goals = goals_result.scalars().all()

        goal_created_dates = {}
        for g in goals:
            goal_created_dates[g.id] = g.created_at

        day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

        for goal in goals:
            created = goal_created_dates.get(goal.id)
            if created:
                weeks_since = max(1, ((week_date - created.date()).days // 7) + 1) if hasattr(created, 'date') else 1
            else:
                weeks_since = 1

            tasks_result = await self.db.execute(
                select(Task)
                .where(
                    Task.goal_id == goal.id,
                    Task.user_id == self.user.id,
                    Task.status.in_(["PENDING", "IN_PROGRESS"]),
                )
                .order_by(Task.week_number.nulls_last(), Task.sort_order)
            )
            all_tasks = tasks_result.scalars().all()

            tasks = [
                t for t in all_tasks
                if t.week_number is None or t.week_number <= weeks_since
            ]

            if not tasks:
                continue

            weekly_budget = float(goal.weekly_hours or 0) * 60
            if weekly_budget <= 0:
                weekly_budget = len(tasks) * 60

            max_per_day = weekly_budget * 0.4
            day_used = {d: 0 for d in day_order}
            budget_used = 0

            for task in tasks:
                if budget_used >= weekly_budget:
                    break

                duration = task.estimated_minutes or 60

                placed = False
                for day in day_order:
                    if day_used[day] + duration > max_per_day:
                        continue

                    slots = free_slots.get(day, [])
                    for si, (slot_start, slot_end) in enumerate(slots):
                        slot_minutes = _time_to_minutes(slot_end) - _time_to_minutes(slot_start)
                        if slot_minutes < duration:
                            continue

                        task_start = slot_start
                        task_end = _minutes_to_time(_time_to_minutes(slot_start) + duration)

                        day_offset = day_map.get(day.lower(), 0)
                        block_date = week_date + timedelta(days=day_offset)

                        block = ScheduleBlock(
                            week_schedule_id=schedule.id,
                            task_id=task.id,
                            goal_id=goal.id,
                            type="GOAL_TASK",
                            day=day,
                            block_date=block_date,
                            start_time=task_start,
                            end_time=task_end,
                            label=task.text,
                            task_description=task.description or "",
                            output_definition=task.output or "",
                            status="SCHEDULED",
                        )
                        self.db.add(block)

                        remaining_start = task_end
                        remaining_end = slot_end
                        if _time_to_minutes(remaining_start) < _time_to_minutes(remaining_end):
                            slots[si] = (remaining_start, remaining_end)
                        else:
                            slots.pop(si)

                        day_used[day] += duration
                        budget_used += duration
                        placed = True
                        break

                    if placed:
                        break

    def _compute_free_slots(self, life_blocks_by_day, day_start="06:00", day_end="23:00"):
        day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        free = {}

        for day in day_order:
            raw = life_blocks_by_day.get(day, [])
            flat_occupied = []
            for occ_start, occ_end in raw:
                occ_s = _time_to_minutes(occ_start)
                occ_e = _time_to_minutes(occ_end)
                if occ_e <= occ_s:
                    flat_occupied.append((occ_s, 24 * 60))
                    flat_occupied.append((0, occ_e))
                else:
                    flat_occupied.append((occ_s, occ_e))

            flat_occupied.sort()

            slots = []
            cursor = _time_to_minutes(day_start)
            end_min = _time_to_minutes(day_end)

            for occ_s, occ_e in flat_occupied:
                if occ_s >= end_min:
                    break
                if occ_e <= cursor:
                    continue
                if occ_s > cursor:
                    slots.append((_minutes_to_time(cursor), _minutes_to_time(min(occ_s, end_min))))
                cursor = max(cursor, occ_e)

            if cursor < end_min:
                slots.append((_minutes_to_time(cursor), _minutes_to_time(end_min)))

            free[day] = slots

        return free

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

        life_blocks_by_day = {}
        for b in schedule.blocks:
            if b.type == "LIFE_BLOCK":
                life_blocks_by_day.setdefault(b.day, []).append((b.start_time, b.end_time))

        for b in schedule.blocks:
            if b.type == "GOAL_TASK" and b.status in ("SCHEDULED", "ACTIVE"):
                await self.db.delete(b)

        await self.db.flush()

        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        await self._place_goal_tasks(schedule, week_date, life_blocks_by_day, day_map)
        await self.db.commit()

        full = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.id == schedule.id)
        )
        return self._week_to_dict(full.scalar_one())

    async def move_block(self, block_id: int, new_day: str, new_time: str):
        result = await self.db.execute(
            select(ScheduleBlock)
            .join(WeekSchedule)
            .where(ScheduleBlock.id == block_id, WeekSchedule.user_id == self.user.id)
        )
        block = result.scalar_one_or_none()
        if not block:
            raise get_error("NOT_FOUND")

        duration = _time_to_minutes(block.end_time) - _time_to_minutes(block.start_time)
        if duration <= 0:
            duration = 60

        block.day = new_day
        block.start_time = new_time
        block.end_time = _minutes_to_time(_time_to_minutes(new_time) + duration)
        block.status = "SCHEDULED"

        week_result = await self.db.execute(
            select(WeekSchedule).where(WeekSchedule.id == block.week_schedule_id)
        )
        week = week_result.scalar_one_or_none()
        if week:
            day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
            day_offset = day_map.get(new_day.lower(), 0)
            block.block_date = week.week_of + timedelta(days=day_offset)

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

    def _week_to_dict(self, schedule, goal_id: int = None):
        blocks = schedule.blocks
        if goal_id:
            blocks = [b for b in blocks if b.goal_id == goal_id]
        return {
            "id": schedule.id,
            "weekOf": str(schedule.week_of),
            "status": schedule.status,
            "lockedAt": schedule.locked_at.isoformat() if schedule.locked_at else None,
            "summaryLine": schedule.summary_line or "",
            "blocks": [self._schedule_block_to_dict(b) for b in blocks],
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
