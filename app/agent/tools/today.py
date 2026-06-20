from app.agent.registry import tool
from app.services.today import TodayService


@tool(description="Get today's scheduled blocks, completion status, and day log")
async def get_today(ctx=None):
    service = TodayService(ctx)
    return await service.get_today()


@tool(description="Mark a scheduled block as DONE, PARTIAL, or MISSED")
async def complete_block(block_id: int, status: str, ctx=None):
    service = TodayService(ctx)
    return await service.complete_block(block_id, status)


@tool(description="Close the day — marks the night review as done and finalizes today's log")
async def close_day(ctx=None):
    service = TodayService(ctx)
    return await service.close_day()
