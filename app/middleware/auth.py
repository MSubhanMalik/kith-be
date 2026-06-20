from fastapi import Depends, Request, Response
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db import get_db
from app.utils import get_error

REFRESH_COOKIE = "kith_refresh"


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


def create_access_token(user_id: int, email: str) -> str:
    from app.services.auth import create_token
    return create_token(user_id, email, "access")


async def get_current_user(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.models import User

    authorization = request.headers.get("Authorization")
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if token:
        try:
            payload = decode_access_token(token)
            if payload.get("token_type") != "access":
                raise get_error("INVALID_TOKEN")
            user_id = payload.get("user_id")
        except ExpiredSignatureError:
            user_id = _try_refresh(request, response)
            if not user_id:
                raise get_error("INVALID_TOKEN")
        except JWTError:
            raise get_error("INVALID_TOKEN")
    else:
        user_id = _try_refresh(request, response)
        if not user_id:
            raise get_error("UNAUTHORIZED")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise get_error("NOT_FOUND", "User not found")

    return user


def _try_refresh(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        return None

    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("token_type") != "refresh":
            return None

        user_id = payload.get("user_id")
        email = payload.get("email")
        if not user_id or not email:
            return None

        new_access = create_access_token(user_id, email)
        response.headers["X-New-Access-Token"] = new_access

        return user_id
    except (JWTError, Exception):
        return None


async def get_optional_user(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        return await get_current_user(request, response, db)
    except Exception:
        return None
