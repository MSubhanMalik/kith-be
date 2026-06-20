from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import StandardResponse

router = APIRouter(prefix="/today", tags=["today"])


@router.get("/", response_model=StandardResponse)
async def get_today(ctx: Context = Depends(get_context)):
    pass


@router.post("/complete/{block_id}", response_model=StandardResponse)
async def complete_task(block_id: int, status: str, ctx: Context = Depends(get_context)):
    pass


@router.post("/close-day", response_model=StandardResponse)
async def close_day(ctx: Context = Depends(get_context)):
    pass
