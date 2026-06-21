from .common import StandardResponse, PaginatedResponse
from .auth import RegisterRequest, LoginRequest, GoogleAuthRequest, TokenResponse
from .goal import (
    CreateGoalRequest, UpdateGoalRequest, ReorderGoalsRequest,
    CreateTaskRequest, UpdateTaskRequest, ReorderTasksRequest,
    CreateNoteRequest, UpdateNoteRequest,
)
from .schedule import CreateLifeBlockRequest, UpdateLifeBlockRequest, GenerateScheduleRequest, MoveTaskRequest, ChatMessageRequest, UpdateSummaryRequest
