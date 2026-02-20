from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.poi_correction import (
    PoiCorrectionListResponse,
    PoiCorrectionResponse,
    PoiCorrectionReviewPayload,
    PoiCorrectionReviewResponse,
    PoiCorrectionTypeListResponse,
)
from app.security.deps import get_current_user
from app.services.poi_correction_service import (
    list_correction_types,
    list_my_corrections,
    list_review_corrections,
    review_correction,
    submit_correction,
)

router = APIRouter(prefix="/corrections", tags=["poi-corrections"])


@router.get("/types", response_model=PoiCorrectionTypeListResponse)
def list_correction_types_api(db: Session = Depends(get_db)) -> PoiCorrectionTypeListResponse:
    return list_correction_types(db)


@router.post("/pois/{poi_id}", response_model=PoiCorrectionResponse)
async def submit_correction_api(
    poi_id: UUID,
    type_code: str = Form(..., min_length=1, max_length=64),
    proposed_value: str | None = Form(default=None),
    details: str | None = Form(default=None),
    source_itinerary_id: UUID | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PoiCorrectionResponse:
    return await submit_correction(
        db=db,
        current_user=current_user,
        poi_id=poi_id,
        type_code=type_code,
        proposed_value=proposed_value,
        details=details,
        photo=photo,
        source_itinerary_id=source_itinerary_id,
    )


@router.get("/mine", response_model=PoiCorrectionListResponse)
def list_my_corrections_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PoiCorrectionListResponse:
    return list_my_corrections(db, current_user, offset, limit)


@router.get("/review", response_model=PoiCorrectionListResponse)
def list_review_corrections_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PoiCorrectionListResponse:
    return list_review_corrections(db, current_user, offset, limit)


@router.post("/{correction_id}/review", response_model=PoiCorrectionReviewResponse)
def review_correction_api(
    correction_id: UUID,
    payload: PoiCorrectionReviewPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PoiCorrectionReviewResponse:
    return review_correction(
        db=db,
        correction_id=correction_id,
        action=payload.action,
        review_comment=payload.review_comment,
        current_user=current_user,
    )
