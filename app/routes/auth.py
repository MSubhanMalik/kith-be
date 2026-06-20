from fastapi import APIRouter, Depends, Request, Response

from app.middleware import Context, get_context, get_public_context
from app.schemas import RegisterRequest, LoginRequest, GoogleAuthRequest, StandardResponse
from app.services.auth import AuthService
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "kith_refresh"
REFRESH_MAX_AGE = settings.JWT_REFRESH_EXPIRES_DAYS * 24 * 60 * 60


def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.ENV == "production",
        samesite="lax",
        max_age=REFRESH_MAX_AGE,
        path="/",
    )


def clear_refresh_cookie(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")


@router.post("/register")
async def register(body: RegisterRequest, response: Response, ctx: Context = Depends(get_public_context)):
    service = AuthService(ctx)
    result = await service.register(body.email, body.password, body.first_name, body.last_name)
    set_refresh_cookie(response, result.pop("refresh_token"))
    return StandardResponse(data=result)


@router.post("/login")
async def login(body: LoginRequest, response: Response, ctx: Context = Depends(get_public_context)):
    service = AuthService(ctx)
    result = await service.login(body.email, body.password)
    set_refresh_cookie(response, result.pop("refresh_token"))
    return StandardResponse(data=result)


@router.post("/google")
async def google_auth(body: GoogleAuthRequest, response: Response, ctx: Context = Depends(get_public_context)):
    service = AuthService(ctx)
    result = await service.google_auth(body.token)
    set_refresh_cookie(response, result.pop("refresh_token"))
    return StandardResponse(data=result)


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, ctx: Context = Depends(get_public_context)):
    token = request.cookies.get(REFRESH_COOKIE_NAME, "")
    if not token:
        return StandardResponse(data=None, message="No refresh token", status=401, success=False)
    service = AuthService(ctx)
    result = await service.refresh(token)
    return StandardResponse(data=result)


@router.get("/me")
async def get_me(ctx: Context = Depends(get_context)):
    user = ctx.require_user()
    service = AuthService(ctx)
    result = await service.get_user_info(user.id)
    return StandardResponse(data=result)


@router.delete("/me")
async def delete_account(response: Response, ctx: Context = Depends(get_context)):
    user = ctx.require_user()
    service = AuthService(ctx)
    await service.delete_account(user.id)
    clear_refresh_cookie(response)
    return StandardResponse(data=None, message="Account deleted")


@router.post("/logout")
async def logout(response: Response):
    clear_refresh_cookie(response)
    return StandardResponse(data=None, message="Logged out")
