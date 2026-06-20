from .auth import router as auth_router
from .goals import router as goals_router
from .tasks import router as tasks_router
from .schedule import router as schedule_router
from .today import router as today_router
from .chat import router as chat_router
from .export import router as export_router

all_routers = [
    auth_router,
    goals_router,
    tasks_router,
    schedule_router,
    today_router,
    chat_router,
    export_router,
]
