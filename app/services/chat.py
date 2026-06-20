from sqlalchemy import select

from app.models import ChatMessage
from app.utils import get_error


class ChatService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def send_message(self, message: str):
        user_msg = ChatMessage(
            user_id=self.user.id,
            role="USER",
            content=message,
        )
        self.db.add(user_msg)
        await self.db.flush()

        reply_text = "I'll be able to help once AI is connected. For now, your message has been saved."

        assistant_msg = ChatMessage(
            user_id=self.user.id,
            role="ASSISTANT",
            content=reply_text,
        )
        self.db.add(assistant_msg)
        await self.db.commit()

        return self._message_to_dict(assistant_msg)

    async def get_history(self):
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == self.user.id)
            .order_by(ChatMessage.created_at)
        )
        return [self._message_to_dict(m) for m in result.scalars().all()]

    def _message_to_dict(self, msg):
        return {
            "id": msg.id,
            "role": msg.role.lower(),
            "content": msg.content,
            "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        }
