from fastapi import APIRouter, Depends, Query

from app.middleware import Context, get_context
from app.schemas import StandardResponse
from app.services.today import TodayService

router = APIRouter(prefix="/today", tags=["today"])


@router.get("/", response_model=StandardResponse)
async def get_today(ctx: Context = Depends(get_context)):
    service = TodayService(ctx)
    result = await service.get_today()
    return StandardResponse(data=result)


@router.post("/complete/{block_id}", response_model=StandardResponse)
async def complete_task(block_id: int, status: str = Query(...), ctx: Context = Depends(get_context)):
    service = TodayService(ctx)
    result = await service.complete_block(block_id, status)
    return StandardResponse(data=result)


@router.post("/close-day", response_model=StandardResponse)
async def close_day(ctx: Context = Depends(get_context)):
    service = TodayService(ctx)
    result = await service.close_day()
    return StandardResponse(data=result, message="Day closed")
