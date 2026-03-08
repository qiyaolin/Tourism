from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- Block domain constants ---
VALID_BLOCK_TYPES = {"scenic", "dining", "lodging", "transit", "note", "shopping", "activity"}
VALID_BLOCK_STATUSES = {"draft", "ready", "running", "done", "blocked"}
VALID_PRIORITY_LEVELS = {"low", "medium", "high"}
VALID_RISK_LEVELS = {"low", "medium", "high"}
VALID_EDGE_TYPES = {"hard", "soft"}


class BlockCreate(BaseModel):
    parent_block_id: UUID | None = None
    sort_order: int = Field(ge=1, le=500, default=1)
    day_index: int = Field(ge=1, le=60, default=1)
    lane_key: str = Field(min_length=1, max_length=32, default="core")
    start_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    end_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    block_type: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    cost: float | None = None
    tips: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = Field(default=None, max_length=255)
    photos: list[str] | None = None
    type_data: dict[str, Any] | None = None
    is_container: bool = False
    source_template_id: UUID | None = None
    status: str = Field(min_length=1, max_length=16, default="draft")
    priority: str = Field(min_length=1, max_length=16, default="medium")
    risk_level: str = Field(min_length=1, max_length=16, default="low")
    assignee_user_id: UUID | None = None
    tags: list[str] | None = None
    ui_meta: dict[str, Any] | None = None


class BlockUpdate(BaseModel):
    parent_block_id: UUID | None = None
    sort_order: int | None = Field(default=None, ge=1, le=500)
    day_index: int | None = Field(default=None, ge=1, le=60)
    lane_key: str | None = Field(default=None, min_length=1, max_length=32)
    start_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    end_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    block_type: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=256)
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    cost: float | None = None
    tips: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = Field(default=None, max_length=255)
    photos: list[str] | None = None
    type_data: dict[str, Any] | None = None
    is_container: bool | None = None
    status: str | None = Field(default=None, min_length=1, max_length=16)
    priority: str | None = Field(default=None, min_length=1, max_length=16)
    risk_level: str | None = Field(default=None, min_length=1, max_length=16)
    assignee_user_id: UUID | None = None
    tags: list[str] | None = None
    ui_meta: dict[str, Any] | None = None


class BlockLayoutUpdate(BaseModel):
    day_index: int | None = Field(default=None, ge=1, le=60)
    lane_key: str | None = Field(default=None, min_length=1, max_length=32)
    start_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    end_minute: int | None = Field(default=None, ge=0, le=24 * 60)
    sort_order: int | None = Field(default=None, ge=1, le=500)


class BlockBatchUpdateRequest(BaseModel):
    itinerary_id: UUID
    block_ids: list[UUID] = Field(min_length=1, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=16)
    priority: str | None = Field(default=None, min_length=1, max_length=16)
    risk_level: str | None = Field(default=None, min_length=1, max_length=16)
    assignee_user_id: UUID | None = None
    tags: list[str] | None = None


class BlockResponse(BaseModel):
    id: UUID
    itinerary_id: UUID
    parent_block_id: UUID | None
    sort_order: int
    day_index: int
    lane_key: str
    start_minute: int | None
    end_minute: int | None
    block_type: str
    title: str
    duration_minutes: int | None
    cost: float | None
    tips: str | None
    longitude: float | None = None
    latitude: float | None = None
    address: str | None
    photos: list[str] | None
    type_data: dict[str, Any] | None
    is_container: bool
    source_template_id: UUID | None
    status: str
    priority: str
    risk_level: str
    assignee_user_id: UUID | None
    tags: list[str] | None
    ui_meta: dict[str, Any] | None
    children: list["BlockResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BlockTreeResponse(BaseModel):
    items: list[BlockResponse]


class BlockReorderRequest(BaseModel):
    parent_block_id: UUID | None = None
    day_index: int = Field(ge=1, le=60)
    ordered_block_ids: list[UUID] = Field(min_length=1, max_length=500)


class BlockDependencyCreate(BaseModel):
    to_block_id: UUID
    edge_type: str = Field(min_length=1, max_length=16, default="hard")


class BlockDependencyResponse(BaseModel):
    id: UUID
    itinerary_id: UUID
    from_block_id: UUID
    to_block_id: UUID
    edge_type: str
    created_at: datetime


class BoardLaneSummary(BaseModel):
    lane_key: str
    label: str
    block_count: int
    done_count: int


class BoardSummary(BaseModel):
    block_count: int
    dependency_count: int
    blocked_count: int


class BoardResponse(BaseModel):
    itinerary_id: UUID
    items: list[BlockResponse]
    dependencies: list[BlockDependencyResponse]
    lanes: list[BoardLaneSummary]
    summary: BoardSummary


class BoardAutoLayoutResponse(BaseModel):
    itinerary_id: UUID
    updated_count: int


class BlockBatchUpdateResponse(BaseModel):
    updated_count: int


class TemplatePublish(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    style_tags: list[str] | None = Field(default=None, max_length=20)
    block_type: str = Field(min_length=1, max_length=32)
    is_group: bool = False
    content_snapshot: dict[str, Any] | None = None
    children_snapshot: list[dict[str, Any]] | None = None
    longitude: float | None = None
    latitude: float | None = None
    region_name: str | None = Field(default=None, max_length=128)


class TemplateResponse(BaseModel):
    id: UUID
    author_id: UUID
    author_nickname: str | None = None
    title: str
    description: str | None
    style_tags: list[str] | None
    block_type: str
    is_group: bool
    content_snapshot: dict[str, Any] | None
    children_snapshot: list[dict[str, Any]] | None
    fork_count: int
    rating_avg: float | None = None
    rating_count: int
    status: str
    region_name: str | None
    created_at: datetime
    updated_at: datetime


class TemplateListQuery(BaseModel):
    block_type: str | None = None
    style_tag: str | None = None
    region_name: str | None = None
    search: str | None = None
    sort_by: str = "hot"  # hot | newest | rating
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    offset: int
    limit: int


class TemplateRatingCreate(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class TemplateRatingResponse(BaseModel):
    id: UUID
    template_id: UUID
    user_id: UUID
    score: int
    comment: str | None
    created_at: datetime


class TemplateForkRequest(BaseModel):
    itinerary_id: UUID
    day_index: int = Field(ge=1, le=60, default=1)
    sort_order: int = Field(ge=1, le=500, default=1)
    lane_key: str = Field(min_length=1, max_length=32, default="core")
    parent_block_id: UUID | None = None
