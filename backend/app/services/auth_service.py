import random
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, SendCodeRequest, SendCodeResponse
from app.security.hashers import (
    bcrypt_hash,
    bcrypt_verify,
    build_phone_lookup_hash,
    normalize_phone,
    validate_phone,
)
from app.security.jwt import create_access_token

CODE_TTL_SECONDS = 300
SEND_INTERVAL_SECONDS = 60
MAX_ATTEMPTS = 5


def _latest_code(db: Session, phone_lookup_hash: str) -> VerificationCode | None:
    stmt = (
        select(VerificationCode)
        .where(
            VerificationCode.phone_lookup_hash == phone_lookup_hash,
            VerificationCode.purpose == "login",
        )
        .order_by(desc(VerificationCode.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def send_code(db: Session, payload: SendCodeRequest) -> SendCodeResponse:
    phone = normalize_phone(payload.phone)
    if not validate_phone(phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone format")

    phone_lookup_hash = build_phone_lookup_hash(phone)
    latest = _latest_code(db, phone_lookup_hash)
    now = datetime.now(UTC)
    if latest and (now - latest.created_at).total_seconds() < SEND_INTERVAL_SECONDS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Code sent too frequently")

    code = f"{random.randint(100000, 999999)}"
    record = VerificationCode(
        phone_lookup_hash=phone_lookup_hash,
        code_hash=bcrypt_hash(code),
        purpose="login",
        expires_at=now + timedelta(seconds=CODE_TTL_SECONDS),
        attempt_count=0,
    )
    db.add(record)
    db.commit()

    settings = get_settings()
    debug_code = code if settings.app_env == "dev" else None
    return SendCodeResponse(success=True, ttl_seconds=CODE_TTL_SECONDS, debug_code=debug_code)


def login_or_register(db: Session, payload: LoginRequest) -> AuthResponse:
    phone = normalize_phone(payload.phone)
    if not validate_phone(phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone format")

    phone_lookup_hash = build_phone_lookup_hash(phone)
    latest = _latest_code(db, phone_lookup_hash)
    now = datetime.now(UTC)
    if latest is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification code not found")
    if latest.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification code already used")
    if latest.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification code expired")
    if latest.attempt_count >= MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification attempts exceeded")

    valid_code = bcrypt_verify(payload.code, latest.code_hash)
    if not valid_code:
        latest.attempt_count += 1
        db.add(latest)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code")

    user_stmt = select(User).where(User.phone_lookup_hash == phone_lookup_hash).limit(1)
    user = db.execute(user_stmt).scalar_one_or_none()
    if user is None:
        nickname = payload.nickname.strip() if payload.nickname else f"用户{phone[-4:]}"
        user = User(
            phone_lookup_hash=phone_lookup_hash,
            phone_hash_bcrypt=bcrypt_hash(phone),
            nickname=nickname,
            role="user",
        )
        db.add(user)

    latest.consumed_at = now
    db.add(latest)
    db.commit()
    db.refresh(user)

    token, expires_in = create_access_token(subject=str(user.id), role=user.role)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=AuthUser(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            role=user.role,
            created_at=user.created_at,
        ),
    )

