from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PoiCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=32)
    longitude: float
    latitude: float
    address: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    ticket_price: float | None = None
    parent_poi_id: UUID | None = None


class PoiUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    type: str | None = Field(default=None, min_length=1, max_length=32)
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    ticket_price: float | None = None
    parent_poi_id: UUID | None = None


class PoiResponse(BaseModel):
    id: UUID
    name: str
    type: str
    longitude: float
    latitude: float
    address: str | None
    opening_hours: str | None
    ticket_price: float | None
    parent_poi_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PoiListResponse(BaseModel):
    items: list[PoiResponse]
    total: int
    offset: int
    limit: int

