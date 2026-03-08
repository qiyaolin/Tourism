from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BountyTaskItem(BaseModel):
    id: UUID
    poi_id: UUID
    poi_name: str
    territory_id: UUID | None
    territory_name: str | None
    status: str
    reward_points: int
    stale_days_snapshot: int
    distance_meters: float | None = None
    generated_at: datetime
    expires_at: datetime | None
    claimed_by_user_id: UUID | None
    claimed_at: datetime | None


class BountyTaskListResponse(BaseModel):
    items: list[BountyTaskItem]
    total: int
    offset: int
    limit: int
    nearby_radius_meters: int | None = None


class BountySubmissionItem(BaseModel):
    id: UUID
    task_id: UUID
    submitter_user_id: UUID
    submit_longitude: float
    submit_latitude: float
    distance_meters: float
    gps_verified: bool
    photo_url: str | None
    photo_exif_captured_at: datetime | None
    photo_exif_longitude: float | None
    photo_exif_latitude: float | None
    risk_level: str
    review_status: str
    reviewer_user_id: UUID | None
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime
    task_status: str
    poi_name: str
    territory_name: str | None
    reward_points: int


class BountySubmissionListResponse(BaseModel):
    items: list[BountySubmissionItem]
    total: int
    offset: int
    limit: int


class BountySubmitResponse(BaseModel):
    task: BountyTaskItem
    submission: BountySubmissionItem
    auto_approved: bool


class BountySubmissionReviewPayload(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    review_comment: str | None = Field(default=None, max_length=2000)

