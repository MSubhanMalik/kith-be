from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import StandardResponse
from app.services.export import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/week/{week_of}", response_model=StandardResponse)
async def export_week(week_of: str, ctx: Context = Depends(get_context)):
    service = ExportService(ctx)
    result = await service.export_week(week_of)
    return StandardResponse(data=result)


@router.get("/goal/{goal_id}", response_model=StandardResponse)
async def export_goal(goal_id: int, ctx: Context = Depends(get_context)):
    service = ExportService(ctx)
    result = await service.export_goal(goal_id)
    return StandardResponse(data=result)
