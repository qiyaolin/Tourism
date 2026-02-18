from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, SendCodeRequest, SendCodeResponse
from app.security.deps import get_current_user
from app.services.auth_service import login_or_register, send_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code", response_model=SendCodeResponse)
def send_login_code(payload: SendCodeRequest, db: Session = Depends(get_db)) -> SendCodeResponse:
    return send_code(db, payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return login_or_register(db, payload)


@router.get("/me", response_model=AuthUser)
def me(current_user: User = Depends(get_current_user)) -> AuthUser:
    return AuthUser(
        id=current_user.id,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        created_at=current_user.created_at,
    )

