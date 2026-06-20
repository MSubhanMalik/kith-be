from datetime import datetime

from sqlalchemy import select, func

from app.models import Goal, Note
from app.utils import get_error

COLOR_ORDER = [
    "terracotta", "sage", "sienna", "slate", "plum",
    "teal", "amber", "clay", "moss", "dusty-rose",
]


def _pick_color(used_colors: list) -> str:
    used = set(used_colors)
    for c in COLOR_ORDER:
        if c not in used:
            return c
    return COLOR_ORDER[0]


class GoalService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def list_goals(self):
        result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == self.user.id, Goal.status != "DELETED")
            .order_by(Goal.rank)
        )
        return [self._goal_to_dict(g) for g in result.scalars().all()]

    async def create_goal(self, data: dict):
        count_result = await self.db.execute(
            select(func.count()).select_from(Goal)
            .where(Goal.user_id == self.user.id, Goal.status != "DELETED")
        )
        if count_result.scalar() >= 10:
            raise get_error("GOAL_LIMIT_REACHED")

        max_rank_result = await self.db.execute(
            select(func.coalesce(func.max(Goal.rank), 0))
            .where(Goal.user_id == self.user.id, Goal.status != "DELETED")
        )
        next_rank = max_rank_result.scalar() + 1

        target_date = None
        if data.get("target_date"):
            target_date = datetime.strptime(data["target_date"], "%Y-%m-%d").date()

        color_id = data.get("color_id")
        if not color_id:
            existing_colors_result = await self.db.execute(
                select(Goal.color_id).where(Goal.user_id == self.user.id, Goal.status != "DELETED")
            )
            used_colors = [r[0] for r in existing_colors_result.all()]
            color_id = _pick_color(used_colors)

        goal = Goal(
            user_id=self.user.id,
            label=data["label"],
            color_id=color_id,
            target_date=target_date,
            weekly_hours=data.get("weekly_hours", 0),
            is_private=data.get("is_private", False),
            nickname=data.get("nickname", ""),
            rank=next_rank,
        )
        self.db.add(goal)
        await self.db.flush()
        await self.db.commit()
        return self._goal_to_dict(goal)

    async def update_goal(self, goal_id: int, data: dict):
        goal = await self._get_goal_or_404(goal_id)

        if "target_date" in data and data["target_date"] is not None:
            data["target_date"] = datetime.strptime(data["target_date"], "%Y-%m-%d").date()

        for key, value in data.items():
            if hasattr(goal, key):
                setattr(goal, key, value)

        await self.db.commit()
        return self._goal_to_dict(goal)

    async def delete_goal(self, goal_id: int):
        goal = await self._get_goal_or_404(goal_id)
        goal.status = "DELETED"
        await self.db.commit()

    async def reorder_goals(self, ordered_ids: list):
        for index, gid in enumerate(ordered_ids):
            result = await self.db.execute(
                select(Goal).where(Goal.id == gid, Goal.user_id == self.user.id)
            )
            goal = result.scalar_one_or_none()
            if goal:
                goal.rank = index + 1
        await self.db.commit()

    async def list_notes(self, goal_id: int):
        await self._get_goal_or_404(goal_id)
        result = await self.db.execute(
            select(Note)
            .where(Note.goal_id == goal_id, Note.user_id == self.user.id, Note.status == "ACTIVE")
            .order_by(Note.created_at.desc())
        )
        return [self._note_to_dict(n) for n in result.scalars().all()]

    async def create_note(self, goal_id: int, text: str):
        await self._get_goal_or_404(goal_id)
        note = Note(goal_id=goal_id, user_id=self.user.id, text=text)
        self.db.add(note)
        await self.db.flush()
        await self.db.commit()
        return self._note_to_dict(note)

    async def update_note(self, goal_id: int, note_id: int, data: dict):
        await self._get_goal_or_404(goal_id)
        result = await self.db.execute(
            select(Note).where(
                Note.id == note_id, Note.goal_id == goal_id, Note.user_id == self.user.id
            )
        )
        note = result.scalar_one_or_none()
        if not note:
            raise get_error("NOT_FOUND")
        for key, value in data.items():
            if hasattr(note, key):
                setattr(note, key, value)
        await self.db.commit()
        return self._note_to_dict(note)

    async def delete_note(self, goal_id: int, note_id: int):
        await self._get_goal_or_404(goal_id)
        result = await self.db.execute(
            select(Note).where(
                Note.id == note_id, Note.goal_id == goal_id, Note.user_id == self.user.id
            )
        )
        note = result.scalar_one_or_none()
        if not note:
            raise get_error("NOT_FOUND")
        note.status = "DELETED"
        await self.db.commit()

    async def _get_goal_or_404(self, goal_id: int):
        result = await self.db.execute(
            select(Goal).where(
                Goal.id == goal_id, Goal.user_id == self.user.id, Goal.status != "DELETED"
            )
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise get_error("NOT_FOUND")
        return goal

    def _goal_to_dict(self, goal):
        return {
            "id": goal.id,
            "label": goal.label,
            "targetDate": str(goal.target_date) if goal.target_date else None,
            "currentStatus": goal.current_status or "",
            "successMetric": goal.success_metric or "",
            "colorId": goal.color_id,
            "rank": goal.rank,
            "weeklyHours": float(goal.weekly_hours) if goal.weekly_hours else 0,
            "isPrivate": goal.is_private,
            "nickname": goal.nickname or "",
            "status": goal.status,
            "createdAt": goal.created_at.isoformat() if goal.created_at else None,
            "updatedAt": goal.updated_at.isoformat() if goal.updated_at else None,
        }

    def _note_to_dict(self, note):
        return {
            "id": note.id,
            "goalId": note.goal_id,
            "text": note.text,
            "status": note.status,
            "createdAt": note.created_at.isoformat() if note.created_at else None,
            "updatedAt": note.updated_at.isoformat() if note.updated_at else None,
        }
