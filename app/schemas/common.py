from typing import Any, Optional
from pydantic import BaseModel


class StandardResponse(BaseModel):
    data: Any = None
    message: str = "Success"
    status: int = 200
    success: bool = True


class PaginatedResponse(StandardResponse):
    total: int = 0
    limit: int = 25
    offset: int = 0
