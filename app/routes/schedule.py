from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import GenerateScheduleRequest, MoveTaskRequest, CreateLifeBlockRequest, StandardResponse

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/week/{week_of}", response_model=StandardResponse)
async def get_week(week_of: str, ctx: Context = Depends(get_context)):
    pass


@router.post("/generate", response_model=StandardResponse)
async def generate_schedule(body: GenerateScheduleRequest, ctx: Context = Depends(get_context)):
    pass


@router.post("/lock/{week_of}", response_model=StandardResponse)
async def lock_schedule(week_of: str, ctx: Context = Depends(get_context)):
    pass


@router.post("/reschedule/{week_of}", response_model=StandardResponse)
async def reschedule(week_of: str, ctx: Context = Depends(get_context)):
    pass


@router.patch("/block/{block_id}/move", response_model=StandardResponse)
async def move_block(block_id: int, body: MoveTaskRequest, ctx: Context = Depends(get_context)):
    pass


@router.get("/life-blocks", response_model=StandardResponse)
async def get_life_blocks(ctx: Context = Depends(get_context)):
    pass


@router.post("/life-blocks", response_model=StandardResponse)
async def create_life_block(body: CreateLifeBlockRequest, ctx: Context = Depends(get_context)):
    pass


@router.delete("/life-blocks/{block_id}", response_model=StandardResponse)
async def delete_life_block(block_id: int, ctx: Context = Depends(get_context)):
    pass
