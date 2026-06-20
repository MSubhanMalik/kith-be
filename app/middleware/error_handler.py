from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.errors import AppError


async def error_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except AppError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "data": None,
                "message": e.detail,
                "status": e.status_code,
                "success": False,
                "error": e.error_code,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "message": str(e),
                "status": 500,
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
            },
        )
