from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.middleware.auth import get_current_user, get_optional_user
from app.utils.errors import get_error


@dataclass
class Context:
    db: AsyncSession
    user: Optional[User]
    request: Request

    def require_user(self) -> User:
        if not self.user:
            raise get_error("UNAUTHORIZED")
        return self.user


async def get_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Context:
    return Context(db=db, user=user, request=request)


async def get_public_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> Context:
    return Context(db=db, user=user, request=request)
