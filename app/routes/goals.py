from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import CreateGoalRequest, UpdateGoalRequest, ReorderGoalsRequest, StandardResponse

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=StandardResponse)
async def get_goals(ctx: Context = Depends(get_context)):
    pass


@router.post("/", response_model=StandardResponse)
async def create_goal(body: CreateGoalRequest, ctx: Context = Depends(get_context)):
    pass


@router.patch("/{goal_id}", response_model=StandardResponse)
async def update_goal(goal_id: int, body: UpdateGoalRequest, ctx: Context = Depends(get_context)):
    pass


@router.delete("/{goal_id}", response_model=StandardResponse)
async def delete_goal(goal_id: int, ctx: Context = Depends(get_context)):
    pass


@router.post("/reorder", response_model=StandardResponse)
async def reorder_goals(body: ReorderGoalsRequest, ctx: Context = Depends(get_context)):
    pass
