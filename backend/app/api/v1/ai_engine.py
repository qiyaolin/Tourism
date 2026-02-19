from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_engine import (
    AiImportRequest,
    AiImportResponse,
    AiPreviewRequest,
    AiPreviewResponse,
)
from app.security.deps import get_current_user
from app.services.ai_engine_service import import_ai_plan, preview_ai_plan

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/preview", response_model=AiPreviewResponse)
def preview_ai_plan_api(
    payload: AiPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiPreviewResponse:
    return preview_ai_plan(db, payload, current_user)


@router.post("/import", response_model=AiImportResponse)
def import_ai_plan_api(
    payload: AiImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiImportResponse:
    return import_ai_plan(db, payload, current_user)
