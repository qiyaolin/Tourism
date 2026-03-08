from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.bounty import (
    BountySubmissionItem,
    BountySubmissionListResponse,
    BountySubmissionReviewPayload,
)
from app.security.deps import require_admin
from app.services.bounty_service import list_admin_bounty_submissions, review_bounty_submission

router = APIRouter(prefix="/admin/bounties", tags=["admin-bounties"])


@router.get("/submissions", response_model=BountySubmissionListResponse)
def list_admin_bounty_submissions_api(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> BountySubmissionListResponse:
    return list_admin_bounty_submissions(
        db,
        review_status_filter=status,
        offset=offset,
        limit=limit,
    )


@router.post("/submissions/{submission_id}/review", response_model=BountySubmissionItem)
def review_bounty_submission_api(
    submission_id: UUID,
    payload: BountySubmissionReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BountySubmissionItem:
    return review_bounty_submission(
        db,
        submission_id=submission_id,
        action=payload.action,
        review_comment=payload.review_comment,
        current_user=current_user,
    )
