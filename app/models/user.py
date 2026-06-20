from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    email_verified = Column(Boolean, default=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    auth_providers = relationship("AuthProvider", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    life_blocks = relationship("LifeBlock", back_populates="user")


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(String(500))
    timezone = Column(String(50), default="UTC")
    morning_review_time = Column(String(5), default="08:00")
    night_review_time = Column(String(5), default="21:00")
    schedule_cycle = Column(String(10), default="WEEKLY")

    user = relationship("User", back_populates="profile")


class AuthProvider(BaseModel):
    __tablename__ = "auth_providers"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_type = Column(String(20), nullable=False)
    provider_key = Column(String(255), nullable=False)
    provider_secret = Column(String(255))
    is_verified = Column(Boolean, default=False)
    status = Column(String(20), default="ACTIVE")

    user = relationship("User", back_populates="auth_providers")


class Session(BaseModel):
    __tablename__ = "sessions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    device_info = Column(String(500))
    expires_at = Column(String(50), nullable=False)


class PasswordResetToken(BaseModel):
    __tablename__ = "password_reset_tokens"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    auth_provider_id = Column(Integer, ForeignKey("auth_providers.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    requested_ip = Column(String(50))


class VerificationOTP(BaseModel):
    __tablename__ = "verification_otp"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
