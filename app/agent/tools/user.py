from app.agent.registry import tool
from sqlalchemy import select, delete
from app.models import UserProfile, ChatMessage


@tool(description="Get the user's profile — name, timezone, review times")
async def get_user_profile(ctx=None):
    db = ctx.db
    user = ctx.require_user()
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    p = result.scalar_one_or_none()
    if not p:
        return {"email": user.email}
    return {
        "email": user.email,
        "firstName": p.first_name,
        "lastName": p.last_name,
        "timezone": p.timezone,
        "morningReviewTime": p.morning_review_time,
        "nightReviewTime": p.night_review_time,
    }


@tool(description="Update user profile settings — name, timezone, morning/night review times")
async def update_user_profile(first_name: str = None, last_name: str = None, timezone: str = None, morning_review_time: str = None, night_review_time: str = None, ctx=None):
    db = ctx.db
    user = ctx.require_user()
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    p = result.scalar_one_or_none()
    if not p:
        return {"error": "Profile not found"}
    if first_name is not None: p.first_name = first_name
    if last_name is not None: p.last_name = last_name
    if timezone is not None: p.timezone = timezone
    if morning_review_time is not None: p.morning_review_time = morning_review_time
    if night_review_time is not None: p.night_review_time = night_review_time
    await db.commit()
    return {"updated": True}


@tool(description="Clear all chat history and start fresh")
async def clear_chat_history(ctx=None):
    db = ctx.db
    user = ctx.require_user()
    await db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    await db.commit()
    return {"cleared": True}


@tool(description="Duplicate a task — creates a copy on a different day or same day")
async def duplicate_task(goal_id: int, task_id: int, new_day: str = None, ctx=None):
    from app.services.task import TaskService
    service = TaskService(ctx)
    tasks = await service.list_tasks(goal_id)
    source = next((t for t in tasks if t["id"] == task_id), None)
    if not source:
        return {"error": "Task not found"}
    return await service.create_task(goal_id, {
        "text": source["text"],
        "description": source["description"],
        "output": source["output"],
        "estimated_minutes": source["estimatedMinutes"],
        "day_of_week": new_day or source["dayOfWeek"],
        "scheduled_time": source["scheduledTime"],
        "week_number": source["weekNumber"],
    })


@tool(description="Move a task to a different week number")
async def move_task_to_week(goal_id: int, task_id: int, new_week_number: int, ctx=None):
    from app.services.task import TaskService
    service = TaskService(ctx)
    return await service.update_task(goal_id, task_id, {"week_number": new_week_number})


@tool(description="Add multiple tasks to a goal in one call")
async def bulk_add_tasks(goal_id: int, tasks: list, ctx=None):
    from app.services.task import TaskService
    service = TaskService(ctx)
    created = []
    for t in tasks:
        result = await service.create_task(goal_id, {
            "text": t.get("text", ""),
            "description": t.get("description"),
            "output": t.get("output"),
            "estimated_minutes": t.get("estimatedMinutes", 60),
            "day_of_week": t.get("dayOfWeek"),
            "scheduled_time": t.get("scheduledTime"),
            "week_number": t.get("weekNumber"),
        })
        created.append(result)
    return {"created": len(created)}


@tool(description="Get a goal's progress history over the last N weeks — tasks done per week")
async def get_goal_history(goal_id: int, weeks: int = 4, ctx=None):
    from sqlalchemy import select, func
    from app.models import WeekSchedule, ScheduleBlock
    from datetime import date, timedelta
    from sqlalchemy.orm import selectinload

    db = ctx.db
    user = ctx.require_user()
    cutoff = date.today() - timedelta(weeks=weeks)

    result = await db.execute(
        select(WeekSchedule)
        .options(selectinload(WeekSchedule.blocks))
        .where(WeekSchedule.user_id == user.id, WeekSchedule.week_of >= cutoff)
        .order_by(WeekSchedule.week_of)
    )
    schedules = result.scalars().all()

    history = []
    for s in schedules:
        goal_blocks = [b for b in s.blocks if b.goal_id == goal_id]
        done = sum(1 for b in goal_blocks if b.status == "COMPLETED")
        history.append({
            "weekOf": str(s.week_of),
            "scheduled": len(goal_blocks),
            "completed": done,
            "summary": s.summary_line or "",
        })

    return {"goalId": goal_id, "weeks": history}
