from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ItineraryWeatherDayResponse(BaseModel):
    day_index: int
    date: date
    text: str
    icon: str
    temp_min: int | None
    temp_max: int | None


class ItineraryWeatherResponse(BaseModel):
    itinerary_id: UUID
    start_date: date
    items: list[ItineraryWeatherDayResponse]
