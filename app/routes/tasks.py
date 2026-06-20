from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import CreateTaskRequest, UpdateTaskRequest, StandardResponse

router = APIRouter(prefix="/goals/{goal_id}/tasks", tags=["tasks"])


@router.get("/", response_model=StandardResponse)
async def get_tasks(goal_id: int, ctx: Context = Depends(get_context)):
    pass


@router.post("/", response_model=StandardResponse)
async def create_task(goal_id: int, body: CreateTaskRequest, ctx: Context = Depends(get_context)):
    pass


@router.patch("/{task_id}", response_model=StandardResponse)
async def update_task(goal_id: int, task_id: int, body: UpdateTaskRequest, ctx: Context = Depends(get_context)):
    pass


@router.delete("/{task_id}", response_model=StandardResponse)
async def delete_task(goal_id: int, task_id: int, ctx: Context = Depends(get_context)):
    pass


@router.post("/reorder", response_model=StandardResponse)
async def reorder_tasks(goal_id: int, ctx: Context = Depends(get_context)):
    pass
