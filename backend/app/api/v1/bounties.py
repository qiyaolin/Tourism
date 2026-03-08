from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.bounty import (
    BountySubmissionListResponse,
    BountySubmitResponse,
    BountyTaskItem,
    BountyTaskListResponse,
)
from app.security.deps import get_current_user
from app.services.bounty_service import (
    claim_bounty_task,
    list_bounty_tasks,
    list_my_bounty_submissions,
    submit_bounty_task,
)

router = APIRouter(prefix="/bounties", tags=["bounties"])


@router.get("", response_model=BountyTaskListResponse)
def list_bounty_tasks_api(
    scope: str = Query(default="all", pattern="^(all|nearby|mine)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    longitude: float | None = Query(default=None),
    latitude: float | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BountyTaskListResponse:
    return list_bounty_tasks(
        db,
        current_user,
        scope=scope,
        offset=offset,
        limit=limit,
        longitude=longitude,
        latitude=latitude,
    )


@router.post("/{task_id}/claim", response_model=BountyTaskItem)
def claim_bounty_task_api(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BountyTaskItem:
    return claim_bounty_task(db, task_id, current_user)


@router.post("/{task_id}/submit", response_model=BountySubmitResponse)
async def submit_bounty_task_api(
    task_id: UUID,
    submit_longitude: float = Form(...),
    submit_latitude: float = Form(...),
    details: str | None = Form(default=None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BountySubmitResponse:
    return await submit_bounty_task(
        db=db,
        task_id=task_id,
        current_user=current_user,
        submit_longitude=submit_longitude,
        submit_latitude=submit_latitude,
        details=details,
        photo=photo,
    )


@router.get("/mine/submissions", response_model=BountySubmissionListResponse)
def list_my_bounty_submissions_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BountySubmissionListResponse:
    return list_my_bounty_submissions(db, current_user, offset=offset, limit=limit)

