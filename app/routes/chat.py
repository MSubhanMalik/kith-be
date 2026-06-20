from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import ChatMessageRequest, StandardResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=StandardResponse)
async def send_message(body: ChatMessageRequest, ctx: Context = Depends(get_context)):
    pass


@router.get("/history", response_model=StandardResponse)
async def get_history(ctx: Context = Depends(get_context)):
    pass
