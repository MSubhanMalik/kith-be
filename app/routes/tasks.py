from fastapi import APIRouter, Depends

from app.middleware import Context, get_context
from app.schemas import CreateTaskRequest, UpdateTaskRequest, ReorderTasksRequest, StandardResponse
from app.services.task import TaskService

router = APIRouter(prefix="/goals/{goal_id}/tasks", tags=["tasks"])


@router.get("/", response_model=StandardResponse)
async def get_tasks(goal_id: int, ctx: Context = Depends(get_context)):
    service = TaskService(ctx)
    result = await service.list_tasks(goal_id)
    return StandardResponse(data=result)


@router.post("/", response_model=StandardResponse)
async def create_task(goal_id: int, body: CreateTaskRequest, ctx: Context = Depends(get_context)):
    service = TaskService(ctx)
    result = await service.create_task(goal_id, body.dict())
    return StandardResponse(data=result, message="Task created")


@router.patch("/{task_id}", response_model=StandardResponse)
async def update_task(goal_id: int, task_id: int, body: UpdateTaskRequest, ctx: Context = Depends(get_context)):
    service = TaskService(ctx)
    result = await service.update_task(goal_id, task_id, body.dict(exclude_unset=True))
    return StandardResponse(data=result)


@router.delete("/{task_id}", response_model=StandardResponse)
async def delete_task(goal_id: int, task_id: int, ctx: Context = Depends(get_context)):
    service = TaskService(ctx)
    await service.delete_task(goal_id, task_id)
    return StandardResponse(data=None, message="Task deleted")


@router.post("/reorder", response_model=StandardResponse)
async def reorder_tasks(goal_id: int, body: ReorderTasksRequest, ctx: Context = Depends(get_context)):
    service = TaskService(ctx)
    await service.reorder_tasks(goal_id, body.ordered_ids)
    return StandardResponse(data=None, message="Tasks reordered")
