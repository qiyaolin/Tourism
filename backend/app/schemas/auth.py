from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SendCodeRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)


class SendCodeResponse(BaseModel):
    success: bool
    ttl_seconds: int
    debug_code: str | None = None


class LoginRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    nickname: str | None = Field(default=None, max_length=64)


class AuthUser(BaseModel):
    id: UUID
    nickname: str
    avatar_url: str | None = None
    role: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser

