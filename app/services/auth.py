from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, UserProfile, AuthProvider
from app.utils import get_error

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, email: str, token_type: str = "access") -> str:
    if token_type == "access":
        expires = timedelta(minutes=settings.JWT_ACCESS_EXPIRES_MINUTES)
    else:
        expires = timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)

    payload = {
        "user_id": user_id,
        "email": email,
        "token_type": token_type,
        "exp": datetime.utcnow() + expires,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


class AuthService:
    def __init__(self, ctx):
        self.db = ctx.db
        self.ctx = ctx

    async def register(self, email: str, password: str, first_name: str = None, last_name: str = None) -> dict:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise get_error("USER_EXISTS")

        user = User(
            email=email,
            status="ACTIVE",
            email_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        profile = UserProfile(
            user_id=user.id,
            first_name=first_name or "",
            last_name=last_name or "",
        )
        self.db.add(profile)
        await self.db.flush()

        provider = AuthProvider(
            user_id=user.id,
            provider_type="EMAIL",
            provider_key=email,
            provider_secret=hash_password(password),
            is_verified=False,
            status="ACTIVE",
        )
        self.db.add(provider)
        await self.db.commit()

        access_token = create_token(user.id, email, "access")
        refresh_token = create_token(user.id, email, "refresh")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": self._user_to_dict(user, profile, [provider]),
        }

    async def login(self, email: str, password: str) -> dict:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise get_error("INVALID_CREDENTIALS")

        provider_result = await self.db.execute(
            select(AuthProvider).where(
                AuthProvider.user_id == user.id,
                AuthProvider.provider_type == "EMAIL",
                AuthProvider.status == "ACTIVE",
            )
        )
        provider = provider_result.scalar_one_or_none()
        if not provider or not provider.provider_secret:
            raise get_error("INVALID_CREDENTIALS")

        if not verify_password(password, provider.provider_secret):
            raise get_error("INVALID_CREDENTIALS")

        profile_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()

        providers_result = await self.db.execute(
            select(AuthProvider).where(AuthProvider.user_id == user.id, AuthProvider.status == "ACTIVE")
        )
        providers = providers_result.scalars().all()

        access_token = create_token(user.id, email, "access")
        refresh_token = create_token(user.id, email, "refresh")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": self._user_to_dict(user, profile, providers),
        }

    async def google_auth(self, id_token: str) -> dict:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
            if resp.status_code != 200:
                raise get_error("INVALID_CREDENTIALS")
            payload = resp.json()

        email = payload.get("email")
        if not email:
            raise get_error("INVALID_CREDENTIALS")

        google_sub = payload.get("sub")
        first_name = payload.get("given_name", "")
        last_name = payload.get("family_name", "")
        picture = payload.get("picture", "")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(email=email, status="ACTIVE", email_verified=True)
            self.db.add(user)
            await self.db.flush()

            profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name, avatar_url=picture)
            self.db.add(profile)
            await self.db.flush()

            provider = AuthProvider(user_id=user.id, provider_type="GOOGLE", provider_key=google_sub, is_verified=True, status="ACTIVE")
            self.db.add(provider)
            await self.db.commit()
        else:
            existing_google = await self.db.execute(
                select(AuthProvider).where(AuthProvider.user_id == user.id, AuthProvider.provider_type == "GOOGLE")
            )
            if not existing_google.scalar_one_or_none():
                self.db.add(AuthProvider(user_id=user.id, provider_type="GOOGLE", provider_key=google_sub, is_verified=True, status="ACTIVE"))
                await self.db.commit()

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        providers_result = await self.db.execute(
            select(AuthProvider).where(AuthProvider.user_id == user.id, AuthProvider.status == "ACTIVE")
        )
        providers = providers_result.scalars().all()

        access_token = create_token(user.id, email, "access")
        refresh_token = create_token(user.id, email, "refresh")

        return {"access_token": access_token, "refresh_token": refresh_token, "user": self._user_to_dict(user, profile, providers)}

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise get_error("INVALID_TOKEN")

        if payload.get("token_type") != "refresh":
            raise get_error("INVALID_TOKEN")

        result = await self.db.execute(select(User).where(User.id == payload["user_id"]))
        user = result.scalar_one_or_none()
        if not user:
            raise get_error("NOT_FOUND")

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        return {"access_token": create_token(user.id, user.email, "access"), "user": self._user_to_dict(user, profile)}

    async def delete_account(self, user_id: int):
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise get_error("NOT_FOUND")

        await self.db.execute(
            AuthProvider.__table__.delete().where(AuthProvider.user_id == user_id)
        )
        await self.db.execute(
            UserProfile.__table__.delete().where(UserProfile.user_id == user_id)
        )
        await self.db.delete(user)
        await self.db.commit()

    async def get_user_info(self, user_id: int) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise get_error("NOT_FOUND")

        profile_result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        providers_result = await self.db.execute(
            select(AuthProvider).where(AuthProvider.user_id == user.id, AuthProvider.status == "ACTIVE")
        )
        providers = providers_result.scalars().all()

        return self._user_to_dict(user, profile, providers)

    def _user_to_dict(self, user, profile=None, providers=None):
        provider_types = [p.provider_type for p in (providers or [])]
        return {
            "id": user.id,
            "email": user.email,
            "firstName": profile.first_name if profile else "",
            "lastName": profile.last_name if profile else "",
            "avatarUrl": profile.avatar_url if profile else "",
            "emailVerified": user.email_verified,
            "providers": provider_types,
        }
