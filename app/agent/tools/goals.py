from app.agent.registry import tool
from app.services.goal import GoalService
from app.services.task import TaskService


@tool(description="Create a new goal for the user")
async def create_goal(label: str, weekly_hours: float = 0, target_date: str = None, is_private: bool = False, nickname: str = None, ctx=None):
    service = GoalService(ctx)
    return await service.create_goal({
        "label": label, "weekly_hours": weekly_hours, "target_date": target_date,
        "is_private": is_private, "nickname": nickname or "",
    })


@tool(description="Get a single goal's details by ID")
async def get_goal(goal_id: int, ctx=None):
    service = GoalService(ctx)
    goals = await service.list_goals()
    return next((g for g in goals if g["id"] == goal_id), None)


@tool(description="Update a goal's properties — label, hours, status, target date, description, privacy")
async def update_goal(goal_id: int, label: str = None, weekly_hours: float = None, target_date: str = None, current_status: str = None, success_metric: str = None, is_private: bool = None, nickname: str = None, ctx=None):
    service = GoalService(ctx)
    data = {}
    if label is not None: data["label"] = label
    if weekly_hours is not None: data["weekly_hours"] = weekly_hours
    if target_date is not None: data["target_date"] = target_date
    if current_status is not None: data["current_status"] = current_status
    if success_metric is not None: data["success_metric"] = success_metric
    if is_private is not None: data["is_private"] = is_private
    if nickname is not None: data["nickname"] = nickname
    return await service.update_goal(goal_id, data)


@tool(description="Delete a goal permanently")
async def delete_goal(goal_id: int, ctx=None):
    service = GoalService(ctx)
    await service.delete_goal(goal_id)
    return {"deleted": True}


@tool(description="Reorder goals by priority — first ID gets rank 1")
async def reorder_goals(ordered_ids: list, ctx=None):
    service = GoalService(ctx)
    await service.reorder_goals(ordered_ids)
    return {"reordered": True}


@tool(description="List all active goals with status and progress")
async def list_goals(ctx=None):
    service = GoalService(ctx)
    return await service.list_goals()


@tool(description="Add a single task to a goal")
async def add_task(goal_id: int, text: str, description: str = None, output: str = None, estimated_minutes: int = None, day_of_week: str = None, scheduled_time: str = None, ctx=None):
    service = TaskService(ctx)
    return await service.create_task(goal_id, {
        "text": text, "description": description, "output": output,
        "estimated_minutes": estimated_minutes, "day_of_week": day_of_week,
        "scheduled_time": scheduled_time,
    })


@tool(description="Update a task's properties — text, description, output, day, time, status")
async def update_task(goal_id: int, task_id: int, text: str = None, description: str = None, output: str = None, day_of_week: str = None, scheduled_time: str = None, status: str = None, estimated_minutes: int = None, ctx=None):
    service = TaskService(ctx)
    data = {}
    if text is not None: data["text"] = text
    if description is not None: data["description"] = description
    if output is not None: data["output"] = output
    if day_of_week is not None: data["day_of_week"] = day_of_week
    if scheduled_time is not None: data["scheduled_time"] = scheduled_time
    if status is not None: data["status"] = status
    if estimated_minutes is not None: data["estimated_minutes"] = estimated_minutes
    return await service.update_task(goal_id, task_id, data)


@tool(description="Remove a single task by ID")
async def remove_task(goal_id: int, task_id: int, ctx=None):
    service = TaskService(ctx)
    await service.delete_task(goal_id, task_id)
    return {"removed": True}


@tool(description="Remove all tasks for a goal")
async def remove_all_tasks(goal_id: int, ctx=None):
    service = TaskService(ctx)
    tasks = await service.list_tasks(goal_id)
    for t in tasks:
        await service.delete_task(goal_id, t["id"])
    return {"removed": len(tasks)}


@tool(description="List all tasks for a specific goal")
async def list_tasks(goal_id: int, ctx=None):
    service = TaskService(ctx)
    return await service.list_tasks(goal_id)


@tool(description="Reorder tasks within a goal")
async def reorder_tasks(goal_id: int, ordered_ids: list, ctx=None):
    service = TaskService(ctx)
    await service.reorder_tasks(goal_id, ordered_ids)
    return {"reordered": True}


@tool(description="Use AI to break a goal into a multi-week plan with concrete tasks, days, and times. Returns immediately — tasks are created in the background.")
async def break_down_goal(goal_id: int, ctx=None):
    from app.services.ai import AIService
    return await AIService(ctx).start_goal_breakdown(goal_id)


@tool(description="Add a note to a goal")
async def add_note(goal_id: int, text: str, ctx=None):
    service = GoalService(ctx)
    return await service.create_note(goal_id, text)


@tool(description="List all notes for a goal")
async def list_notes(goal_id: int, ctx=None):
    service = GoalService(ctx)
    return await service.list_notes(goal_id)


@tool(description="Delete a note from a goal")
async def remove_note(goal_id: int, note_id: int, ctx=None):
    service = GoalService(ctx)
    await service.delete_note(goal_id, note_id)
    return {"removed": True}
