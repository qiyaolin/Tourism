from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PoiCorrectionTypeResponse(BaseModel):
    id: UUID
    code: str
    label: str
    target_field: str
    value_kind: str
    placeholder: str | None
    input_mode: Literal["ticket_rules", "time_range", "text"]
    input_schema: dict | None
    help_text: str | None
    sort_order: int


class PoiCorrectionTypeListResponse(BaseModel):
    items: list[PoiCorrectionTypeResponse]


class PoiCorrectionResponse(BaseModel):
    id: UUID
    poi_id: UUID
    territory_id: UUID | None = None
    territory_name: str | None = None
    source_poi_name_snapshot: str | None
    source_itinerary_id: UUID | None
    source_itinerary_title_snapshot: str | None
    source_itinerary_author_snapshot: str | None
    type_code: str
    type_label: str
    target_field: str
    value_kind: str
    proposed_value: str | None
    details: str | None
    photo_url: str | None
    status: str
    submitter_user_id: UUID
    reviewer_user_id: UUID | None
    review_comment: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None


class PoiCorrectionListResponse(BaseModel):
    items: list[PoiCorrectionResponse]
    total: int
    offset: int
    limit: int


class PoiCorrectionReviewPayload(BaseModel):
    action: str = Field(pattern="^(accepted|rejected)$")
    review_comment: str | None = Field(default=None, max_length=1000)


class PoiCorrectionReviewResponse(BaseModel):
    correction: PoiCorrectionResponse
    poi_updated: bool
