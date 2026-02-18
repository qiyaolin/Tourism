from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


class ItineraryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    destination: str = Field(min_length=1, max_length=64)
    days: int = Field(gt=0, le=60)
    status: str = Field(default="draft")
    visibility: str = Field(default="private")


class ItineraryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    destination: str | None = Field(default=None, min_length=1, max_length=64)
    days: int | None = Field(default=None, gt=0, le=60)
    status: str | None = None
    visibility: str | None = None


class ItineraryResponse(BaseModel):
    id: UUID
    title: str
    destination: str
    days: int
    creator_user_id: UUID
    status: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class ItineraryListResponse(BaseModel):
    items: list[ItineraryResponse]
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
