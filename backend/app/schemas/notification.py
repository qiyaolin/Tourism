from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserNotificationResponse(BaseModel):
    id: UUID
    recipient_user_id: UUID
    sender_user_id: UUID | None
    event_type: str
    severity: str
    title: str
    content: str
    is_read: bool
    read_at: datetime | None
    source_itinerary_id: UUID | None
    forked_itinerary_id: UUID | None
    source_snapshot_id: UUID | None
    correction_id: UUID | None
    poi_id: UUID | None
    extra_payload: dict
    created_at: datetime
    updated_at: datetime


class UserNotificationListResponse(BaseModel):
    items: list[UserNotificationResponse]
    total: int
    unread_count: int
    offset: int
    limit: int


class MarkNotificationReadRequest(BaseModel):
    read: bool = Field(default=True)


class MarkAllNotificationsReadResponse(BaseModel):
    updated_count: int
