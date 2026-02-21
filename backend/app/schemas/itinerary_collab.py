from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ItineraryCollabLinkCreateRequest(BaseModel):
    permission: Literal["edit", "read"] = "edit"


class ItineraryCollabLinkUpdateRequest(BaseModel):
    permission: Literal["edit", "read"] | None = None
    revoke: bool | None = None


class ItineraryCollabLinkResponse(BaseModel):
    id: UUID
    itinerary_id: UUID
    permission: Literal["edit", "read"]
    is_revoked: bool
    created_by_user_id: UUID
    created_at: datetime
    revoked_at: datetime | None


class ItineraryCollabLinkCreateResponse(BaseModel):
    link: ItineraryCollabLinkResponse
    token: str
    share_url: str


class ItineraryCollabLinkListResponse(BaseModel):
    items: list[ItineraryCollabLinkResponse]


class ItineraryCollabHistoryItem(BaseModel):
    id: UUID
    itinerary_id: UUID
    actor_type: Literal["system", "user", "guest"]
    actor_user_id: UUID | None
    guest_name: str | None
    event_type: str
    target_type: str | None
    target_id: str | None
    payload: dict
    created_at: datetime


class ItineraryCollabHistoryListResponse(BaseModel):
    items: list[ItineraryCollabHistoryItem]
    total: int
    offset: int
    limit: int


class ItineraryCollabParticipant(BaseModel):
    session_id: str
    participant_type: Literal["user", "guest"]
    display_name: str
    permission: Literal["edit", "read"]
    joined_at: datetime
    cursor: dict | None = None


class ItineraryCollabWsJoinedPayload(BaseModel):
    itinerary_id: UUID
    permission: Literal["edit", "read"]
    participants: list[ItineraryCollabParticipant] = Field(default_factory=list)
    snapshot_update_b64: str | None = None
    needs_seed: bool = False
