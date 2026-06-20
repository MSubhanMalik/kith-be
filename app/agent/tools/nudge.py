from app.agent.registry import tool
from app.services.nudge import NudgeService


@tool(description="Send a nudge message to the user from the cat — used for block transitions, reminders, and goal-aware observations")
async def send_nudge(nudge_type: str, message: str, schedule_block_id: int = None, ctx=None):
    service = NudgeService(ctx)
    return await service.create_nudge(nudge_type, message, schedule_block_id)


@tool(description="Get all active undismissed nudges for the user from the last 24 hours")
async def get_active_nudges(ctx=None):
    service = NudgeService(ctx)
    return await service.list_active()


@tool(description="Dismiss a nudge by ID so it no longer shows to the user")
async def dismiss_nudge(nudge_id: int, ctx=None):
    service = NudgeService(ctx)
    await service.dismiss(nudge_id)
    return {"dismissed": True}
