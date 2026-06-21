from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import ChatMessageRequest, StandardResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=StandardResponse)
async def send_message(body: ChatMessageRequest, ctx: Context = Depends(get_context)):
    service = ChatService(ctx)
    result = await service.send_message(body.message, body.page_context)
    return StandardResponse(data=result)


@router.get("/history", response_model=StandardResponse)
async def get_history(ctx: Context = Depends(get_context)):
    service = ChatService(ctx)
    result = await service.get_history()
    return StandardResponse(data=result)


@router.post("/nudge", response_model=StandardResponse)
async def generate_nudge(ctx: Context = Depends(get_context)):
    from app.services.ai import AIService
    service = AIService(ctx)
    nudge = await service.generate_cat_message("on_demand")
    return StandardResponse(data=nudge)
