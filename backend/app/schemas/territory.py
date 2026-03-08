from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TerritoryGuardianBrief(BaseModel):
    user_id: UUID
    nickname: str
    role: str
    state: str
    granted_at: datetime


class TerritoryRegionItem(BaseModel):
    id: UUID
    code: str
    name: str
    status: str
    poi_count: int
    boundary_wkt: str | None
    centroid_wkt: str | None
    guardians: list[TerritoryGuardianBrief]
    sample_pois: list[str] = []


class TerritoryRegionListResponse(BaseModel):
    items: list[TerritoryRegionItem]


class TerritoryGuardianApplicationCreatePayload(BaseModel):
    territory_id: UUID
    reason: str | None = Field(default=None, max_length=2000)


class TerritoryGuardianApplicationResponse(BaseModel):
    id: UUID
    territory_id: UUID
    territory_name: str
    applicant_user_id: UUID
    applicant_nickname: str
    reason: str | None
    status: str
    reviewer_user_id: UUID | None
    reviewer_nickname: str | None
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime


class TerritoryGuardianApplicationListResponse(BaseModel):
    items: list[TerritoryGuardianApplicationResponse]
    total: int
    offset: int
    limit: int


class TerritoryGuardianApplicationReviewPayload(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    review_comment: str | None = Field(default=None, max_length=2000)


class TerritoryRebuildResponse(BaseModel):
    generated_regions: int
    assigned_pois: int
    inactive_regions: int


class TerritoryGuardianCheckInResponse(BaseModel):
    territory_id: UUID
    guardian_user_id: UUID
    checked_in_at: datetime


# ---------- New: role-based profile & task center ----------


class UserTerritoryRoleItem(BaseModel):
    territory_id: UUID
    territory_name: str
    role: str  # regular / local_expert / area_guide / city_ambassador
    state: str  # active / dormant / honorary
    contribution_count: int
    thanks_received: int
    next_role: str | None
    next_role_progress: float  # 0.0 ~ 1.0


class UserTerritoryProfileResponse(BaseModel):
    user_id: UUID
    roles: list[UserTerritoryRoleItem]
    total_contributions: int
    total_thanks: int


class TaskCenterItem(BaseModel):
    task_type: str  # pending_review / poi_verification / nearby_opportunity / bounty
    title: str
    territory_name: str
    territory_id: UUID
    target_id: UUID | None
    points: int
    created_at: datetime


class TaskCenterResponse(BaseModel):
    pending_reviews: int
    items: list[TaskCenterItem]
    monthly_contributions: int
    monthly_helped_count: int

class TerritoryOpportunityResponse(BaseModel):
    territory_id: UUID
    items: list[TaskCenterItem]
