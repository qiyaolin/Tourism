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


class PoiTicketRuleItem(BaseModel):
    id: UUID
    audience_code: str
    audience_label: str
    ticket_type: str
    time_slot: str
    price: float
    currency: str
    conditions: str | None
    is_active: bool


class PoiTicketRuleUpsert(BaseModel):
    id: UUID | None = None
    audience_code: str = Field(min_length=1, max_length=32)
    ticket_type: str = Field(min_length=1, max_length=64)
    time_slot: str = Field(min_length=1, max_length=64)
    price: float = Field(ge=0)
    currency: str = Field(default="CNY", min_length=3, max_length=8)
    conditions: str | None = None
    is_active: bool = True


class PoiTicketRuleBatchUpsert(BaseModel):
    items: list[PoiTicketRuleUpsert] = Field(min_length=1, max_length=100)


class PricingAudienceItem(BaseModel):
    code: str
    label: str
    sort_order: int


class PricingAudienceListResponse(BaseModel):
    items: list[PricingAudienceItem]


class PoiTicketRuleListResponse(BaseModel):
    items: list[PoiTicketRuleItem]


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
    ticket_rules: list[PoiTicketRuleItem] = Field(default_factory=list)
    parent_poi_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PoiListResponse(BaseModel):
    items: list[PoiResponse]
    total: int
    offset: int
    limit: int
