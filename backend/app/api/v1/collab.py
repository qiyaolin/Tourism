from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.itinerary_collab import CollabCodeResolveRequest, CollabCodeResolveResponse
from app.security.deps import get_current_user
from app.services.collab_service import resolve_collab_code_for_user

router = APIRouter(prefix="/collab", tags=["itinerary-collab"])


@router.post(
    "/code/resolve",
    response_model=CollabCodeResolveResponse,
    status_code=status.HTTP_200_OK,
)
def resolve_collab_code_api(
    payload: CollabCodeResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollabCodeResolveResponse:
    return resolve_collab_code_for_user(db, current_user=current_user, payload=payload)
