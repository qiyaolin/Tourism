from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkAllNotificationsReadResponse,
    MarkNotificationReadRequest,
    UserNotificationListResponse,
    UserNotificationResponse,
)
from app.security.deps import get_current_user
from app.services.notification_service import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=UserNotificationListResponse)
def list_notifications_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserNotificationListResponse:
    return list_notifications(db, current_user, offset, limit, unread_only)


@router.post("/{notification_id}/read", response_model=UserNotificationResponse)
def mark_notification_read_api(
    notification_id: UUID,
    payload: MarkNotificationReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserNotificationResponse:
    return mark_notification_read(db, notification_id, current_user, payload.read)


@router.post("/read-all", response_model=MarkAllNotificationsReadResponse)
def mark_all_notifications_read_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkAllNotificationsReadResponse:
    return mark_all_notifications_read(db, current_user)
