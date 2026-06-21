import json
import time as timer

from sqlalchemy import select

from app.models import ChatMessage
from app.config import settings
from app.services.llm import LLMClient
from app.services.ai import AIService
from app.services.context_builder import ContextBuilder
from app.agent import get_tool_schemas, execute_tool


SYSTEM_PROMPT_TEMPLATE = """You are Kith, a cat companion that helps {name} stay on track with their goals.

PERSONALITY:
- Smart roommate, not a boss. Think friend who has your calendar open.
- Lead with data, then ask a question. Never judge. Never nag.
- Casual tone. No emojis. No exclamation marks.
- When you take actions (move tasks, create tasks), confirm what you did in plain language.

RESPONSE FORMAT — THIS IS MANDATORY, NEVER VIOLATE:
- MAXIMUM 2 sentences. No exceptions. Ever.
- NEVER list tasks, schedules, days, or times in your response. NEVER.
- After using tools, respond ONLY with a short confirmation like "Done — 8 tasks created for your goal." or "Week rescheduled."
- Do NOT use markdown formatting (no **, no ##, no bullet points, no lists).
- Do NOT summarize what the tools returned. The user can see it in the app.
- Plain text only. Short. Direct.

{context}

RULES:
- When the user asks to reschedule or make changes, USE THE TOOLS to do it. Don't just suggest.
- When breaking down a goal, use break_down_goal with the goal_id. Do NOT list the tasks in your response.
- For schedule questions, call get_today or get_week first to see current state before answering.
- Never fabricate data. If you don't have info, say so.
- If a user asks something unrelated to goals or scheduling, answer briefly and steer back.

SAFETY:
- Preserve the user's work. Relocate, don't remove. Check state before changing it."""


class ChatService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()
        self.ctx = ctx

    async def send_message(self, message: str, page_context: dict = None):
        ai_service = AIService(self.ctx)

        if not settings.OPENROUTER_API_KEY:
            return await self._placeholder_reply(message)

        ai_run = await ai_service.run("CHAT", message)
        start = timer.time()

        user_msg = ChatMessage(
            user_id=self.user.id, role="USER", content=message, ai_run_id=ai_run.id
        )
        self.db.add(user_msg)
        await self.db.flush()

        context_builder = ContextBuilder(self.ctx)
        context = await context_builder.build_chat_context(page_context)
        context_text = context_builder.format_for_prompt(context)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            name=context.get("userName", "there"),
            context=context_text,
        )

        history = await self._get_recent_history()

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": message},
        ]

        tools = get_tool_schemas()
        llm = LLMClient()
        total_tokens = 0
        all_tool_calls = []
        reply_text = "Something went wrong. Try again?"

        try:
            for _ in range(settings.LLM_MAX_TOOL_ITERATIONS):
                response = await llm.chat_with_fallback(
                    messages=messages,
                    model=settings.OPENROUTER_MODEL_SMART,
                    tools=tools if tools else None,
                    temperature=0.7,
                )

                if response.usage:
                    total_tokens += response.usage.total_tokens

                choice = response.choices[0]

                if choice.message.tool_calls:
                    assistant_msg_dict = {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            }
                            for tc in choice.message.tool_calls
                        ],
                    }
                    if choice.message.content:
                        assistant_msg_dict["content"] = choice.message.content
                    messages.append(assistant_msg_dict)

                    for tc in choice.message.tool_calls:
                        try:
                            arguments = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                        result = await execute_tool(tc.function.name, arguments, self.ctx)
                        all_tool_calls.append({
                            "name": tc.function.name,
                            "arguments": arguments,
                            "result": result,
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, default=str),
                        })
                    continue

                reply_text = choice.message.content or reply_text
                break

        except Exception as e:
            import traceback
            traceback.print_exc()
            await ai_service.fail_run(ai_run.id, str(e))
            reply_text = f"Something went wrong: {str(e)[:100]}"

        duration_ms = int((timer.time() - start) * 1000)

        assistant_msg = ChatMessage(
            user_id=self.user.id,
            role="ASSISTANT",
            content=reply_text,
            ai_run_id=ai_run.id,
            tool_calls=json.dumps(all_tool_calls, default=str) if all_tool_calls else None,
        )
        self.db.add(assistant_msg)
        await self.db.commit()

        await ai_service.complete_run(ai_run.id, reply_text, total_tokens, duration_ms)

        return self._message_to_dict(assistant_msg)

    async def get_history(self):
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == self.user.id)
            .order_by(ChatMessage.created_at)
        )
        return [self._message_to_dict(m) for m in result.scalars().all()]

    async def _get_recent_history(self):
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == self.user.id,
                ChatMessage.role.in_(["USER", "ASSISTANT"]),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(settings.LLM_CHAT_HISTORY_LIMIT)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role.lower(), "content": m.content} for m in messages]

    async def _placeholder_reply(self, message: str):
        user_msg = ChatMessage(user_id=self.user.id, role="USER", content=message)
        self.db.add(user_msg)
        await self.db.flush()

        reply = ChatMessage(
            user_id=self.user.id,
            role="ASSISTANT",
            content="I need an API key to think. Add OPENROUTER_API_KEY to your .env file and restart.",
        )
        self.db.add(reply)
        await self.db.commit()
        return self._message_to_dict(reply)

    def _message_to_dict(self, msg):
        return {
            "id": msg.id,
            "role": msg.role.lower(),
            "content": msg.content,
            "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        }
