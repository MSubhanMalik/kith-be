from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import (
    CreateGoalRequest, UpdateGoalRequest, ReorderGoalsRequest,
    CreateNoteRequest, UpdateNoteRequest, StandardResponse,
)
from app.services.goal import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=StandardResponse)
async def get_goals(ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.list_goals()
    return StandardResponse(data=result)


@router.post("/", response_model=StandardResponse)
async def create_goal(body: CreateGoalRequest, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.create_goal(body.dict())
    return StandardResponse(data=result, message="Goal created")


@router.patch("/{goal_id}", response_model=StandardResponse)
async def update_goal(goal_id: int, body: UpdateGoalRequest, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.update_goal(goal_id, body.dict(exclude_unset=True))
    return StandardResponse(data=result)


@router.delete("/{goal_id}", response_model=StandardResponse)
async def delete_goal(goal_id: int, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    await service.delete_goal(goal_id)
    return StandardResponse(data=None, message="Goal deleted")


@router.post("/reorder", response_model=StandardResponse)
async def reorder_goals(body: ReorderGoalsRequest, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    await service.reorder_goals(body.ordered_ids)
    return StandardResponse(data=None, message="Goals reordered")


@router.post("/{goal_id}/breakdown", response_model=StandardResponse)
async def breakdown_goal(goal_id: int, ctx: Context = Depends(get_context)):
    from app.services.ai import AIService
    service = AIService(ctx)
    tasks = await service.break_goal_into_tasks(goal_id)
    return StandardResponse(data=tasks, message="Goal broken down into tasks")


@router.get("/{goal_id}/notes", response_model=StandardResponse)
async def get_notes(goal_id: int, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.list_notes(goal_id)
    return StandardResponse(data=result)


@router.post("/{goal_id}/notes", response_model=StandardResponse)
async def create_note(goal_id: int, body: CreateNoteRequest, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.create_note(goal_id, body.text)
    return StandardResponse(data=result, message="Note created")


@router.patch("/{goal_id}/notes/{note_id}", response_model=StandardResponse)
async def update_note(goal_id: int, note_id: int, body: UpdateNoteRequest, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    result = await service.update_note(goal_id, note_id, body.dict(exclude_unset=True))
    return StandardResponse(data=result)


@router.delete("/{goal_id}/notes/{note_id}", response_model=StandardResponse)
async def delete_note(goal_id: int, note_id: int, ctx: Context = Depends(get_context)):
    service = GoalService(ctx)
    await service.delete_note(goal_id, note_id)
    return StandardResponse(data=None, message="Note deleted")
