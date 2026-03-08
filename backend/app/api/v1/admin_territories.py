from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.territory import (
    TerritoryGuardianApplicationListResponse,
    TerritoryGuardianApplicationResponse,
    TerritoryGuardianApplicationReviewPayload,
    TerritoryRebuildResponse,
)
from app.security.deps import require_admin
from app.services.territory_service import (
    list_guardian_applications,
    rebuild_territory_regions,
    review_guardian_application,
)

router = APIRouter(prefix="/admin/territories", tags=["admin-territories"])


@router.get("/applications", response_model=TerritoryGuardianApplicationListResponse)
def list_guardian_applications_api(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TerritoryGuardianApplicationListResponse:
    return list_guardian_applications(db, status, offset, limit)


@router.post(
    "/applications/{application_id}/review",
    response_model=TerritoryGuardianApplicationResponse,
)
def review_guardian_application_api(
    application_id: UUID,
    payload: TerritoryGuardianApplicationReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TerritoryGuardianApplicationResponse:
    return review_guardian_application(
        db,
        application_id=application_id,
        action=payload.action,
        review_comment=payload.review_comment,
        current_user=current_user,
    )


@router.post("/rebuild", response_model=TerritoryRebuildResponse)
def rebuild_territories_api(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TerritoryRebuildResponse:
    return rebuild_territory_regions(db)
