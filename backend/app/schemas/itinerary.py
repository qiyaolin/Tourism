from datetime import datetime, time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ItineraryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    destination: str = Field(min_length=1, max_length=64)
    days: int = Field(gt=0, le=60)
    status: str = Field(default="draft")
    visibility: str = Field(default="private")
    cover_image_url: str | None = Field(default=None, max_length=512)


class ItineraryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    destination: str | None = Field(default=None, min_length=1, max_length=64)
    days: int | None = Field(default=None, gt=0, le=60)
    status: str | None = None
    visibility: str | None = None
    cover_image_url: str | None = Field(default=None, max_length=512)


class ItineraryResponse(BaseModel):
    id: UUID
    title: str
    destination: str
    days: int
    creator_user_id: UUID
    status: str
    visibility: str
    cover_image_url: str | None
    fork_source_itinerary_id: UUID | None = None
    fork_source_author_nickname: str | None = None
    fork_source_title: str | None = None
    created_at: datetime
    updated_at: datetime


class ItineraryListResponse(BaseModel):
    items: list[ItineraryResponse]
    total: int
    offset: int
    limit: int


class PublicItineraryResponse(BaseModel):
    id: UUID
    title: str
    destination: str
    days: int
    status: str
    visibility: str
    cover_image_url: str | None
    author_nickname: str
    forked_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicItineraryListResponse(BaseModel):
    items: list[PublicItineraryResponse]
    total: int
    offset: int
    limit: int


class ItineraryItemCreate(BaseModel):
    day_index: int = Field(ge=1, le=60)
    sort_order: int = Field(ge=1, le=200)
    poi_id: UUID
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    cost: float | None = None
    tips: str | None = None


class ItineraryItemUpdate(BaseModel):
    day_index: int | None = Field(default=None, ge=1, le=60)
    sort_order: int | None = Field(default=None, ge=1, le=200)
    poi_id: UUID | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    cost: float | None = None
    tips: str | None = None


class ItineraryItemResponse(BaseModel):
    id: UUID
    itinerary_id: UUID
    day_index: int
    sort_order: int
    poi_id: UUID
    start_time: time | None
    duration_minutes: int | None
    cost: float | None
    tips: str | None
    created_at: datetime
    updated_at: datetime


class ItineraryItemPoiSnapshot(BaseModel):
    id: UUID
    name: str
    type: str
    longitude: float
    latitude: float
    address: str | None
    opening_hours: str | None
    ticket_price: float | None


class ItineraryItemWithPoiResponse(BaseModel):
    item_id: UUID
    itinerary_id: UUID
    day_index: int
    sort_order: int
    start_time: time | None
    duration_minutes: int | None
    cost: float | None
    tips: str | None
    poi: ItineraryItemPoiSnapshot


class ItineraryItemsWithPoiListResponse(BaseModel):
    items: list[ItineraryItemWithPoiResponse]


class ForkItineraryResponse(BaseModel):
    new_itinerary_id: UUID
    title: str
    source_itinerary_id: UUID
    source_author_nickname: str
    source_title: str


class ItineraryFieldDiff(BaseModel):
    field: str
    before: Any
    after: Any


class ItineraryDiffItemAdded(BaseModel):
    key: str
    current: dict[str, Any]


class ItineraryDiffItemRemoved(BaseModel):
    key: str
    source: dict[str, Any]


class ItineraryDiffItemModified(BaseModel):
    key: str
    fields: list[ItineraryFieldDiff]


class ItineraryDiffSummary(BaseModel):
    added: int
    removed: int
    modified: int


class ItineraryDiffResponse(BaseModel):
    source_snapshot_id: UUID
    source_itinerary_id: UUID
    forked_itinerary_id: UUID
    latest_source_snapshot_id: UUID | None = None
    stale_warning: bool = False
    summary: ItineraryDiffSummary
    metadata_diffs: list[ItineraryFieldDiff]
    added_items: list[ItineraryDiffItemAdded]
    removed_items: list[ItineraryDiffItemRemoved]
    modified_items: list[ItineraryDiffItemModified]
    action_statuses: dict[str, str] = Field(default_factory=dict)


class ItineraryDiffActionInput(BaseModel):
    diff_key: str = Field(min_length=1, max_length=128)
    diff_type: Literal["metadata", "added", "removed", "modified"]
    action: Literal["applied", "rolled_back", "ignored", "read"]
    reason: str | None = Field(default=None, max_length=500)


class ItineraryDiffActionBatchRequest(BaseModel):
    source_snapshot_id: UUID
    actions: list[ItineraryDiffActionInput] = Field(min_length=1, max_length=100)


class ItineraryDiffActionBatchResponse(BaseModel):
    applied_count: int
    rolled_back_count: int
    ignored_count: int
    read_count: int
    warnings: list[str] = Field(default_factory=list)
    action_statuses: dict[str, str] = Field(default_factory=dict)


class ItineraryDiffActionStatusItem(BaseModel):
    diff_key: str
    diff_type: str
    action: str
    reason: str | None
    actor_user_id: UUID
    created_at: datetime


class ItineraryDiffActionStatusResponse(BaseModel):
    source_snapshot_id: UUID
    items: list[ItineraryDiffActionStatusItem]
