from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models import Goal, Task, WeekSchedule, ScheduleBlock, DayLog, TaskCompletion, WeekMetric


class ContextBuilder:
    def __init__(self, ctx):
        self.db = ctx.db
        self.user = ctx.require_user()

    async def build_chat_context(self, page_context: dict = None):
        goals = await self._get_goals_with_counts()
        today_blocks = await self._get_today_blocks()
        history = await self._get_week_history()
        today = date.today()

        context = {
            "goals": goals,
            "todayBlocks": today_blocks,
            "weekHistory": history,
            "currentTime": today.isoformat(),
            "dayOfWeek": today.strftime("%A"),
            "userName": self.user.email.split("@")[0],
            "pageContext": page_context,
        }

        if page_context and page_context.get("goalId"):
            focused = await self._get_focused_goal(page_context["goalId"])
            if focused:
                context["focusedGoal"] = focused

        return context

    def format_for_prompt(self, context):
        lines = []
        lines.append(f"TODAY: {context['dayOfWeek']} {context['currentTime']}")
        lines.append("")

        if context.get("pageContext"):
            pc = context["pageContext"]
            screen = pc.get("screen", "home")
            if screen == "goal" and context.get("focusedGoal"):
                fg = context["focusedGoal"]
                lines.append(f"USER IS VIEWING GOAL: \"{fg['label']}\" (id: {fg['id']})")
                lines.append(f"  Tasks: {fg['doneTasks']}/{fg['totalTasks']} done, {fg['pendingTasks']} pending")
                if fg.get("recentTasks"):
                    lines.append(f"  Recent tasks: {', '.join(fg['recentTasks'][:5])}")
                lines.append("")
            elif screen == "week":
                lines.append("USER IS VIEWING: Week schedule")
                lines.append("")
            elif screen == "review":
                lines.append("USER IS VIEWING: End of day review")
                lines.append("")

        if context["goals"]:
            lines.append("GOALS (by priority):")
            for g in context["goals"]:
                status = f", {g['pendingTasks']} pending, {g['doneTasks']} done" if g['totalTasks'] > 0 else ""
                target = f", target: {g['targetDate']}" if g.get('targetDate') else ""
                lines.append(f"  #{g['rank']} [{g['label']}] id:{g['id']}, {g['weeklyHours']}h/wk{status}{target}")
        else:
            lines.append("GOALS: none yet")

        lines.append("")

        if context["todayBlocks"]:
            lines.append("TODAY'S SCHEDULE:")
            for b in context["todayBlocks"]:
                status_mark = "DONE" if b["status"] in ("COMPLETED", "DONE") else "PENDING"
                goal_tag = f" ({b['goalName']})" if b.get("goalName") else ""
                lines.append(f"  {b['startTime']}-{b['endTime']} {b['label']}{goal_tag} [{status_mark}]")
        else:
            lines.append("TODAY'S SCHEDULE: nothing scheduled")

        if context.get("weekHistory"):
            lines.append("")
            lines.append("RECENT WEEKS:")
            for wh in context["weekHistory"]:
                summary = wh.get("summaryLine") or "no summary"
                lines.append(f"  {wh['weekOf']}: {wh['tasksDone']}/{wh['tasksPlanned']} tasks — \"{summary}\"")

        return "\n".join(lines)

    async def _get_goals_with_counts(self):
        result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == self.user.id, Goal.status != "DELETED")
            .order_by(Goal.rank)
        )
        goals = result.scalars().all()

        goal_list = []
        for g in goals:
            total_result = await self.db.execute(
                select(func.count()).select_from(Task)
                .where(Task.goal_id == g.id, Task.user_id == self.user.id, Task.status != "DELETED")
            )
            total = total_result.scalar()

            done_result = await self.db.execute(
                select(func.count()).select_from(Task)
                .where(Task.goal_id == g.id, Task.user_id == self.user.id, Task.status == "DONE")
            )
            done = done_result.scalar()

            goal_list.append({
                "id": g.id,
                "label": g.label,
                "rank": g.rank,
                "weeklyHours": float(g.weekly_hours) if g.weekly_hours else 0,
                "targetDate": str(g.target_date) if g.target_date else None,
                "currentStatus": g.current_status or "",
                "totalTasks": total,
                "pendingTasks": total - done,
                "doneTasks": done,
            })

        return goal_list

    async def _get_today_blocks(self):
        today = date.today()
        day_name = today.strftime("%a").upper()[:3]
        monday = today - timedelta(days=today.weekday())

        week_result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(WeekSchedule.user_id == self.user.id, WeekSchedule.week_of == monday)
        )
        schedule = week_result.scalar_one_or_none()
        if not schedule:
            return []

        log_result = await self.db.execute(
            select(DayLog).where(DayLog.user_id == self.user.id, DayLog.date == today)
        )
        day_log = log_result.scalar_one_or_none()

        completions = {}
        if day_log:
            comp_result = await self.db.execute(
                select(TaskCompletion).where(TaskCompletion.day_log_id == day_log.id)
            )
            completions = {tc.schedule_block_id: tc.status for tc in comp_result.scalars().all()}

        blocks = []
        for b in schedule.blocks:
            if b.day != day_name:
                continue

            goal_result = await self.db.execute(
                select(Goal).where(Goal.id == b.goal_id)
            ) if b.goal_id else None
            goal = goal_result.scalar_one_or_none() if goal_result else None

            blocks.append({
                "id": b.id,
                "label": b.label,
                "startTime": b.start_time,
                "endTime": b.end_time,
                "type": b.type,
                "status": completions.get(b.id, b.status),
                "goalName": goal.label if goal else None,
            })

        blocks.sort(key=lambda x: x["startTime"])
        return blocks

    async def _get_week_history(self):
        four_weeks_ago = date.today() - timedelta(weeks=4)
        result = await self.db.execute(
            select(WeekSchedule)
            .options(selectinload(WeekSchedule.blocks))
            .where(
                WeekSchedule.user_id == self.user.id,
                WeekSchedule.week_of >= four_weeks_ago,
                WeekSchedule.status.in_(["LOCKED", "COMPLETED"]),
            )
            .order_by(WeekSchedule.week_of.desc())
            .limit(4)
        )
        schedules = result.scalars().all()

        history = []
        for s in schedules:
            goal_blocks = [b for b in s.blocks if b.type == "GOAL_TASK"]
            done = sum(1 for b in goal_blocks if b.status == "COMPLETED")
            history.append({
                "weekOf": str(s.week_of),
                "tasksPlanned": len(goal_blocks),
                "tasksDone": done,
                "summaryLine": s.summary_line or "",
            })

        return history

    async def _get_focused_goal(self, goal_id: int):
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == self.user.id)
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return None

        tasks_result = await self.db.execute(
            select(Task)
            .where(Task.goal_id == goal_id, Task.user_id == self.user.id, Task.status != "DELETED")
            .order_by(Task.sort_order)
            .limit(10)
        )
        tasks = tasks_result.scalars().all()

        total = len(tasks)
        done = sum(1 for t in tasks if t.status == "DONE")

        return {
            "id": goal.id,
            "label": goal.label,
            "totalTasks": total,
            "doneTasks": done,
            "pendingTasks": total - done,
            "recentTasks": [t.text for t in tasks if t.status != "DONE"][:5],
        }
