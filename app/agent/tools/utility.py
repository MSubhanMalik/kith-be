from datetime import date, datetime, timedelta

from app.agent.registry import tool


@tool(description="Get the current date, time, and day of week")
async def get_current_time(ctx=None):
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "dayOfWeek": now.strftime("%A"),
        "weekOf": (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d"),
    }


@tool(description="Calculate the number of days between two dates")
async def days_between(start_date: str, end_date: str, ctx=None):
    s = datetime.strptime(start_date, "%Y-%m-%d").date()
    e = datetime.strptime(end_date, "%Y-%m-%d").date()
    diff = (e - s).days
    weeks = diff // 7
    return {"days": diff, "weeks": weeks}


@tool(description="Get the Monday date for a given week offset from today (0=this week, 1=next week, -1=last week)")
async def get_week_date(offset: int = 0, ctx=None):
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    return {
        "weekOf": monday.strftime("%Y-%m-%d"),
        "monday": monday.strftime("%Y-%m-%d"),
        "sunday": sunday.strftime("%Y-%m-%d"),
        "label": f"{monday.strftime('%b %d')} – {sunday.strftime('%d')}",
    }


@tool(description="Search across all goals and tasks for a keyword")
async def search(query: str, ctx=None):
    from sqlalchemy import select, or_
    from app.models import Goal, Task
    db = ctx.db
    user = ctx.require_user()

    goal_results = await db.execute(
        select(Goal).where(
            Goal.user_id == user.id, Goal.status != "DELETED",
            or_(Goal.label.ilike(f"%{query}%"), Goal.current_status.ilike(f"%{query}%"))
        )
    )
    goals = [{"type": "goal", "id": g.id, "label": g.label} for g in goal_results.scalars().all()]

    task_results = await db.execute(
        select(Task).where(
            Task.user_id == user.id, Task.status != "DELETED",
            or_(Task.text.ilike(f"%{query}%"), Task.description.ilike(f"%{query}%"))
        )
    )
    tasks = [{"type": "task", "id": t.id, "goalId": t.goal_id, "text": t.text} for t in task_results.scalars().all()]

    return {"results": goals + tasks, "count": len(goals) + len(tasks)}


@tool(description="Get a summary of overall progress — all goals, completion rates, hours this week")
async def get_progress_summary(ctx=None):
    from sqlalchemy import select, func
    from app.models import Goal, Task
    db = ctx.db
    user = ctx.require_user()

    goals_result = await db.execute(
        select(Goal).where(Goal.user_id == user.id, Goal.status != "DELETED").order_by(Goal.rank)
    )
    goals = goals_result.scalars().all()

    summary = []
    total_tasks = 0
    total_done = 0

    for g in goals:
        t_count = (await db.execute(
            select(func.count()).select_from(Task).where(Task.goal_id == g.id, Task.status != "DELETED")
        )).scalar()
        d_count = (await db.execute(
            select(func.count()).select_from(Task).where(Task.goal_id == g.id, Task.status == "DONE")
        )).scalar()
        total_tasks += t_count
        total_done += d_count
        summary.append({
            "goal": g.label,
            "rank": g.rank,
            "weeklyHours": float(g.weekly_hours) if g.weekly_hours else 0,
            "tasksDone": d_count,
            "tasksTotal": t_count,
            "targetDate": str(g.target_date) if g.target_date else None,
        })

    return {
        "goals": summary,
        "totalGoals": len(goals),
        "totalTasks": total_tasks,
        "totalDone": total_done,
        "completionRate": round(total_done / total_tasks * 100) if total_tasks > 0 else 0,
    }


@tool(description="Calculate how many weeks until a target date at the current pace")
async def pace_check(goal_id: int, ctx=None):
    from sqlalchemy import select, func
    from app.models import Goal, Task
    db = ctx.db
    user = ctx.require_user()

    goal_result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id)
    )
    goal = goal_result.scalar_one_or_none()
    if not goal:
        return {"error": "Goal not found"}

    total = (await db.execute(
        select(func.count()).select_from(Task).where(Task.goal_id == goal_id, Task.status != "DELETED")
    )).scalar()
    done = (await db.execute(
        select(func.count()).select_from(Task).where(Task.goal_id == goal_id, Task.status == "DONE")
    )).scalar()
    remaining = total - done

    if goal.target_date:
        days_left = (goal.target_date - date.today()).days
        weeks_left = max(1, days_left // 7)
        tasks_per_week = remaining / weeks_left if weeks_left > 0 else remaining
    else:
        days_left = None
        weeks_left = None
        tasks_per_week = None

    created_days = (date.today() - goal.created_at.date()).days if goal.created_at else 0
    weeks_elapsed = max(1, created_days // 7)
    current_pace = done / weeks_elapsed if weeks_elapsed > 0 else 0
    weeks_to_finish = remaining / current_pace if current_pace > 0 else None

    return {
        "goal": goal.label,
        "tasksDone": done,
        "tasksRemaining": remaining,
        "tasksTotal": total,
        "daysUntilTarget": days_left,
        "weeksUntilTarget": weeks_left,
        "currentPacePerWeek": round(current_pace, 1),
        "requiredPacePerWeek": round(tasks_per_week, 1) if tasks_per_week else None,
        "estimatedWeeksToFinish": round(weeks_to_finish, 1) if weeks_to_finish else None,
        "onTrack": (weeks_to_finish <= weeks_left) if weeks_to_finish and weeks_left else None,
    }
