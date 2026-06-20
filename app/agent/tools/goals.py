from typing import Optional

from app.agent.registry import tool
from app.services.goal import GoalService
from app.services.task import TaskService


@tool(description="Create a new goal for the user with a label and optional time allocation")
async def create_goal(label: str, weekly_hours: float = 0, target_date: str = None, ctx=None):
    service = GoalService(ctx)
    return await service.create_goal({
        "label": label,
        "weekly_hours": weekly_hours,
        "target_date": target_date,
    })


@tool(description="Update an existing goal's properties like label, hours, status, or target date")
async def update_goal(goal_id: int, label: str = None, weekly_hours: float = None, target_date: str = None, current_status: str = None, ctx=None):
    service = GoalService(ctx)
    data = {}
    if label is not None:
        data["label"] = label
    if weekly_hours is not None:
        data["weekly_hours"] = weekly_hours
    if target_date is not None:
        data["target_date"] = target_date
    if current_status is not None:
        data["current_status"] = current_status
    return await service.update_goal(goal_id, data)


@tool(description="Reorder the user's goals by priority — first ID gets rank 1")
async def reorder_goals(ordered_ids: list, ctx=None):
    service = GoalService(ctx)
    await service.reorder_goals(ordered_ids)
    return {"reordered": True}


@tool(description="List all active goals for the user with their current status and progress")
async def list_goals(ctx=None):
    service = GoalService(ctx)
    return await service.list_goals()


@tool(description="Add a task to a goal's task queue with text and optional output definition")
async def add_task(goal_id: int, text: str, description: str = None, output: str = None, estimated_minutes: int = None, ctx=None):
    service = TaskService(ctx)
    return await service.create_task(goal_id, {
        "text": text,
        "description": description,
        "output": output,
        "estimated_minutes": estimated_minutes,
    })


@tool(description="Mark a task's status as DONE, PENDING, or SKIPPED")
async def update_task_status(goal_id: int, task_id: int, status: str, ctx=None):
    service = TaskService(ctx)
    return await service.update_task(goal_id, task_id, {"status": status})


@tool(description="List all tasks for a specific goal")
async def list_tasks(goal_id: int, ctx=None):
    service = TaskService(ctx)
    return await service.list_tasks(goal_id)


@tool(description="Break a goal into multiple concrete tasks with time estimates. Returns the created tasks.")
async def break_down_goal(goal_id: int, tasks: list, ctx=None):
    service = TaskService(ctx)
    created = []
    for t in tasks:
        result = await service.create_task(goal_id, {
            "text": t.get("text", ""),
            "description": t.get("description"),
            "output": t.get("output"),
            "estimated_minutes": t.get("estimatedMinutes"),
            "day_of_week": t.get("dayOfWeek"),
        })
        created.append(result)
    return created
