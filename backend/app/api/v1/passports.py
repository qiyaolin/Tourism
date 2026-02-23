from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.passport import PassportResponse
from app.security.deps import get_current_user
from app.services.passport_service import get_user_passport

router = APIRouter()


@router.get("/me", response_model=PassportResponse)
def get_my_passport(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's digital passport, including points, level, and badges.
    """
    data = get_user_passport(db, current_user.id)
    return data
