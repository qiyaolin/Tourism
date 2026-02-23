from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TerritoryGuardianBrief(BaseModel):
    user_id: UUID
    nickname: str
    state: str
    granted_at: datetime


class TerritoryRegionItem(BaseModel):
    id: UUID
    code: str
    name: str
    status: str
    poi_count: int
    boundary_wkt: str
    centroid_wkt: str
    guardians: list[TerritoryGuardianBrief]


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


class TerritoryGuardianReputationItem(BaseModel):
    guardian_id: UUID
    territory_id: UUID
    territory_name: str
    guardian_user_id: UUID
    guardian_nickname: str
    guardian_state: str
    reviewed_count: int
    accepted_count: int
    accuracy: float
    threshold: float
    status: str
    calculated_at: datetime


class TerritoryGuardianReputationListResponse(BaseModel):
    items: list[TerritoryGuardianReputationItem]


class TerritoryGuardianResumeResponse(BaseModel):
    guardian_id: UUID
    territory_id: UUID
    state: str
    updated_at: datetime
