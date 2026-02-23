from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.territory import (
    TerritoryGuardianApplicationCreatePayload,
    TerritoryGuardianApplicationResponse,
    TerritoryGuardianCheckInResponse,
    TerritoryRegionItem,
    TerritoryRegionListResponse,
)
from app.security.deps import get_current_user
from app.services.territory_service import (
    get_territory,
    guardian_check_in,
    list_territories,
    submit_guardian_application,
)

router = APIRouter(prefix="/territories", tags=["territories"])


@router.get("", response_model=TerritoryRegionListResponse)
def list_territories_api(db: Session = Depends(get_db)) -> TerritoryRegionListResponse:
    return list_territories(db)


@router.get("/{territory_id}", response_model=TerritoryRegionItem)
def get_territory_api(
    territory_id: UUID,
    db: Session = Depends(get_db),
) -> TerritoryRegionItem:
    return get_territory(db, territory_id)


@router.post("/applications", response_model=TerritoryGuardianApplicationResponse)
def submit_guardian_application_api(
    payload: TerritoryGuardianApplicationCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TerritoryGuardianApplicationResponse:
    return submit_guardian_application(db, payload, current_user)


@router.post("/{territory_id}/check-in", response_model=TerritoryGuardianCheckInResponse)
def guardian_check_in_api(
    territory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TerritoryGuardianCheckInResponse:
    return guardian_check_in(db, territory_id, current_user)
