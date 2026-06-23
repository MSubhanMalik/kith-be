from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.middleware import Context, get_context
from app.schemas import (
    GenerateScheduleRequest, MoveTaskRequest,
    CreateLifeBlockRequest, UpdateLifeBlockRequest, StandardResponse,
    UpdateSummaryRequest,
)
from app.services.scheduler import ScheduleService

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/week/{week_of}", response_model=StandardResponse)
async def get_week(week_of: str, goal_id: Optional[int] = Query(None), ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.get_week(week_of, goal_id=goal_id)
    return StandardResponse(data=result)


@router.post("/generate", response_model=StandardResponse)
async def generate_schedule(body: GenerateScheduleRequest, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.generate_schedule(body.week_of)
    return StandardResponse(data=result, message="Schedule generated")


@router.post("/lock/{week_of}", response_model=StandardResponse)
async def lock_schedule(week_of: str, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.lock_week(week_of)
    return StandardResponse(data=result, message="Schedule locked")


@router.post("/reschedule/{week_of}", response_model=StandardResponse)
async def reschedule(week_of: str, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.reschedule_week(week_of)
    return StandardResponse(data=result)


@router.patch("/week/{week_of}/summary", response_model=StandardResponse)
async def update_summary(week_of: str, body: UpdateSummaryRequest, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    await service.update_summary(week_of, body.summary_line)
    return StandardResponse(data=None, message="Summary saved")


@router.patch("/block/{block_id}/move", response_model=StandardResponse)
async def move_block(block_id: int, body: MoveTaskRequest, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.move_block(block_id, body.new_day, body.new_time)
    return StandardResponse(data=result)


@router.get("/life-blocks", response_model=StandardResponse)
async def get_life_blocks(ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.list_life_blocks()
    return StandardResponse(data=result)


@router.post("/life-blocks", response_model=StandardResponse)
async def create_life_block(body: CreateLifeBlockRequest, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.create_life_block(body.dict())
    return StandardResponse(data=result, message="Life block created")


@router.patch("/life-blocks/{block_id}", response_model=StandardResponse)
async def update_life_block(block_id: int, body: UpdateLifeBlockRequest, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    result = await service.update_life_block(block_id, body.dict(exclude_unset=True))
    return StandardResponse(data=result)


@router.delete("/life-blocks/{block_id}", response_model=StandardResponse)
async def delete_life_block(block_id: int, ctx: Context = Depends(get_context)):
    service = ScheduleService(ctx)
    await service.delete_life_block(block_id)
    return StandardResponse(data=None, message="Life block deleted")
