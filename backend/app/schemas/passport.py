import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BadgeDefResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    icon_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class UserBadgeResponse(BaseModel):
    id: uuid.UUID
    badge_id: uuid.UUID
    created_at: datetime
    badge_def: BadgeDefResponse
    model_config = ConfigDict(from_attributes=True)


class UserContributionResponse(BaseModel):
    id: uuid.UUID
    action_type: str
    points: int
    created_at: datetime
    source_id: uuid.UUID | None = None
    model_config = ConfigDict(from_attributes=True)


class PassportResponse(BaseModel):
    user_id: uuid.UUID
    total_points: int
    level: int
    badges: list[UserBadgeResponse]
    recent_contributions: list[UserContributionResponse]
