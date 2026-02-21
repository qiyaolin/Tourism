from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.weather import ItineraryWeatherResponse
from app.security.deps import get_current_user
from app.services.weather_service import get_itinerary_weather

router = APIRouter(prefix="/itineraries", tags=["weather"])


@router.get("/{itinerary_id}/weather", response_model=ItineraryWeatherResponse)
def get_itinerary_weather_api(
    itinerary_id: UUID,
    force_refresh: bool = Query(default=False),
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryWeatherResponse:
    return get_itinerary_weather(
        db,
        itinerary_id,
        current_user,
        collab_grant=collab_grant,
        force_refresh=force_refresh,
    )
