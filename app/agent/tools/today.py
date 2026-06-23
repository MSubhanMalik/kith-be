from datetime import date, timedelta

from app.agent.registry import tool
from app.services.today import TodayService


@tool(description="Get today's scheduled blocks, completion status, and day log")
async def get_today(ctx=None):
    service = TodayService(ctx)
    return await service.get_today()


@tool(description="Get tomorrow's scheduled blocks")
async def get_tomorrow(ctx=None):
    service = TodayService(ctx)
    tomorrow = date.today() + timedelta(days=1)
    return await service.get_today(target_date=tomorrow)


@tool(description="Get a specific day's schedule and completion status")
async def get_day(target_date: str, ctx=None):
    from datetime import datetime
    service = TodayService(ctx)
    d = datetime.strptime(target_date, "%Y-%m-%d").date()
    return await service.get_today(target_date=d)


@tool(description="Mark a scheduled block as DONE, PARTIAL, or MISSED")
async def complete_block(block_id: int, status: str, ctx=None):
    service = TodayService(ctx)
    return await service.complete_block(block_id, status)


@tool(description="Close the day — finalize today's log")
async def close_day(ctx=None):
    service = TodayService(ctx)
    return await service.close_day()
