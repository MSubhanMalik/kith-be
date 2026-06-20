from fastapi import APIRouter, Depends

from app.middleware import Context, get_context

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/week/{week_of}")
async def export_week(week_of: str, ctx: Context = Depends(get_context)):
    pass


@router.get("/goal/{goal_id}")
async def export_goal(goal_id: int, ctx: Context = Depends(get_context)):
    pass
