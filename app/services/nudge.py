from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import Nudge


class NudgeService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def list_active(self):
        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await self.db.execute(
            select(Nudge)
            .where(
                Nudge.user_id == self.user.id,
                Nudge.dismissed == False,
                Nudge.created_at >= cutoff,
            )
            .order_by(Nudge.created_at.desc())
        )
        return [self._to_dict(n) for n in result.scalars().all()]

    async def create_nudge(self, nudge_type: str, message: str, schedule_block_id: int = None):
        nudge = Nudge(
            user_id=self.user.id,
            type=nudge_type,
            message=message,
            schedule_block_id=schedule_block_id,
        )
        self.db.add(nudge)
        await self.db.flush()
        await self.db.commit()
        return self._to_dict(nudge)

    async def dismiss(self, nudge_id: int):
        result = await self.db.execute(
            select(Nudge).where(Nudge.id == nudge_id, Nudge.user_id == self.user.id)
        )
        nudge = result.scalar_one_or_none()
        if nudge:
            nudge.dismissed = True
            nudge.dismissed_at = datetime.utcnow()
            await self.db.commit()

    async def clear_old(self):
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(Nudge).where(
                Nudge.user_id == self.user.id,
                Nudge.created_at < cutoff,
            )
        )
        for nudge in result.scalars().all():
            await self.db.delete(nudge)
        await self.db.commit()

    def _to_dict(self, nudge):
        return {
            "id": nudge.id,
            "type": nudge.type,
            "message": nudge.message,
            "scheduledBlockId": nudge.schedule_block_id,
            "dismissed": nudge.dismissed,
            "triggeredAt": nudge.created_at.isoformat() if nudge.created_at else None,
        }
