from app.agent.registry import tool
from app.services.scheduler import ScheduleService


@tool(description="Generate a weekly schedule from the user's goals, tasks, and life blocks for a given week")
async def generate_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.generate_schedule(week_of)


@tool(description="Lock the weekly schedule so it becomes the user's commitment for that week")
async def lock_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.lock_week(week_of)


@tool(description="Redistribute incomplete or missed tasks across the remaining days of the week")
async def rebalance_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.reschedule_week(week_of)


@tool(description="Move a scheduled block to a different day and time slot")
async def swap_block(block_id: int, new_day: str, new_time: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.move_block(block_id, new_day, new_time)


@tool(description="Get the full weekly schedule for a given week")
async def get_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.get_week(week_of)


@tool(description="Save a one-line summary for the week written by the user")
async def save_week_summary(week_of: str, summary: str, ctx=None):
    service = ScheduleService(ctx)
    await service.update_summary(week_of, summary)
    return {"weekOf": week_of, "summary": summary}
