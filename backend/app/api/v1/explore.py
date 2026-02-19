from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.itinerary import (
    ForkItineraryResponse,
    ItineraryItemsWithPoiListResponse,
    PublicItineraryListResponse,
    PublicItineraryResponse,
)
from app.security.deps import get_current_user
from app.services.itinerary_service import (
    fork_public_itinerary,
    get_public_itinerary,
    list_public_items_with_poi,
    list_public_itineraries,
)

router = APIRouter(prefix="/explore", tags=["explore"])


@router.get("/itineraries", response_model=PublicItineraryListResponse)
def list_public_itineraries_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PublicItineraryListResponse:
    return list_public_itineraries(db, offset, limit)


@router.get("/itineraries/{itinerary_id}", response_model=PublicItineraryResponse)
def get_public_itinerary_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> PublicItineraryResponse:
    return get_public_itinerary(db, itinerary_id)


@router.get("/itineraries/{itinerary_id}/items", response_model=ItineraryItemsWithPoiListResponse)
def list_public_items_with_poi_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> ItineraryItemsWithPoiListResponse:
    return list_public_items_with_poi(db, itinerary_id)


@router.post(
    "/itineraries/{itinerary_id}/fork",
    response_model=ForkItineraryResponse,
    status_code=201,
)
def fork_public_itinerary_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ForkItineraryResponse:
    return fork_public_itinerary(db, itinerary_id, current_user)
