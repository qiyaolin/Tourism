from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.itinerary import (
    ExploreHeatPointListResponse,
    ExploreRecommendationListResponse,
    ExploreVisitLogResponse,
    ForkItineraryResponse,
    ItineraryItemsWithPoiListResponse,
    PublicItineraryListResponse,
    PublicItineraryResponse,
    PublicItineraryShareMetaResponse,
)
from app.security.deps import get_current_user, get_current_user_optional
from app.services.itinerary_service import (
    fork_public_itinerary,
    get_public_itinerary,
    get_public_itinerary_share_meta,
    list_explore_heatmap,
    list_explore_recommendations,
    list_public_items_with_poi,
    list_public_itineraries,
    record_public_itinerary_view,
)

router = APIRouter(prefix="/explore", tags=["explore"])


@router.get("/itineraries", response_model=PublicItineraryListResponse)
def list_public_itineraries_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PublicItineraryListResponse:
    return list_public_itineraries(db, offset, limit)


@router.get("/heatmap", response_model=ExploreHeatPointListResponse)
def list_explore_heatmap_api(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ExploreHeatPointListResponse:
    return list_explore_heatmap(db, limit)


@router.get("/recommendations", response_model=ExploreRecommendationListResponse)
def list_explore_recommendations_api(
    limit: int = Query(default=12, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ExploreRecommendationListResponse:
    return list_explore_recommendations(db, current_user, limit)


@router.get("/itineraries/{itinerary_id}", response_model=PublicItineraryResponse)
def get_public_itinerary_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> PublicItineraryResponse:
    return get_public_itinerary(db, itinerary_id)


@router.get("/itineraries/{itinerary_id}/share-meta", response_model=PublicItineraryShareMetaResponse)
def get_public_itinerary_share_meta_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> PublicItineraryShareMetaResponse:
    return get_public_itinerary_share_meta(db, itinerary_id)


@router.get("/itineraries/{itinerary_id}/items", response_model=ItineraryItemsWithPoiListResponse)
def list_public_items_with_poi_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> ItineraryItemsWithPoiListResponse:
    return list_public_items_with_poi(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/view", response_model=ExploreVisitLogResponse, status_code=201)
def record_public_itinerary_view_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExploreVisitLogResponse:
    return record_public_itinerary_view(db, itinerary_id, current_user)


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
