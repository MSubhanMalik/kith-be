from app.agent.registry import tool
from app.services.scheduler import ScheduleService


@tool(description="Generate a weekly schedule placing tasks into time slots around life blocks")
async def generate_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.generate_schedule(week_of)


@tool(description="Lock the weekly schedule as a commitment")
async def lock_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.lock_week(week_of)


@tool(description="Redistribute tasks across remaining days of the week")
async def rebalance_week(week_of: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.reschedule_week(week_of)


@tool(description="Move a scheduled block to a different day and time")
async def swap_block(block_id: int, new_day: str, new_time: str, ctx=None):
    service = ScheduleService(ctx)
    return await service.move_block(block_id, new_day, new_time)


@tool(description="Get the full weekly schedule for a given week, optionally filtered by goal")
async def get_week(week_of: str, goal_id: int = None, ctx=None):
    service = ScheduleService(ctx)
    return await service.get_week(week_of, goal_id=goal_id)


@tool(description="Save a one-line summary for the week")
async def save_week_summary(week_of: str, summary: str, ctx=None):
    service = ScheduleService(ctx)
    await service.update_summary(week_of, summary)
    return {"saved": True}


@tool(description="List all life blocks (non-negotiable recurring time blocks like Work, Gym, Sleep)")
async def get_life_blocks(ctx=None):
    service = ScheduleService(ctx)
    return await service.list_life_blocks()


@tool(description="Create a life block — a recurring non-negotiable time block")
async def create_life_block(label: str, start_time: str, end_time: str, days: list, ctx=None):
    service = ScheduleService(ctx)
    return await service.create_life_block({
        "label": label, "start_time": start_time, "end_time": end_time, "days": days,
    })


@tool(description="Remove a life block")
async def remove_life_block(block_id: int, ctx=None):
    service = ScheduleService(ctx)
    await service.delete_life_block(block_id)
    return {"removed": True}
