from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AiPreviewRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=12000)
    itinerary_id: UUID


class AiPreviewPoi(BaseModel):
    poi_id: UUID | None = None
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=32)
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    ticket_price: float | None = None
    match_source: Literal["local", "amap", "unresolved"]


class AiPreviewItem(BaseModel):
    day_index: int = Field(ge=1, le=60)
    sort_order: int = Field(ge=1, le=200)
    start_time: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    cost: float | None = None
    tips: str | None = None
    poi: AiPreviewPoi


class AiPreviewResponse(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    destination: str = Field(min_length=1, max_length=64)
    days: int = Field(ge=1, le=60)
    items: list[AiPreviewItem]


class AiImportRequest(BaseModel):
    itinerary_id: UUID
    preview: AiPreviewResponse


class AiImportResponse(BaseModel):
    imported_count: int
