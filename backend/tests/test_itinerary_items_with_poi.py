from datetime import time
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.services.itinerary_service import list_items_with_poi


def test_list_items_with_poi_returns_sorted_items():
    owner_id = uuid4()
    itinerary_id = uuid4()
    poi_id = uuid4()
    item_id = uuid4()

    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id)
    user = SimpleNamespace(id=owner_id)
    item = SimpleNamespace(
        id=item_id,
        itinerary_id=itinerary_id,
        day_index=1,
        sort_order=2,
        start_time=time(hour=9, minute=30),
        duration_minutes=90,
        cost=Decimal("55.50"),
        tips="Wear sneakers",
    )
    poi = SimpleNamespace(
        id=poi_id,
        name="Hangzhou West Lake",
        type="sightseeing",
        address="Xihu District",
        opening_hours="09:00-18:00",
        ticket_price=Decimal("80.00"),
    )

    db = SimpleNamespace()
    db.get = lambda model, entity_id: itinerary
    db.execute = lambda stmt: SimpleNamespace(all=lambda: [(item, poi, "POINT(120.1536 30.2875)")])

    result = list_items_with_poi(db, itinerary_id, user)

    assert len(result.items) == 1
    payload = result.items[0]
    assert payload.item_id == item_id
    assert payload.day_index == 1
    assert payload.sort_order == 2
    assert payload.cost == 55.5
    assert payload.poi.id == poi_id
    assert payload.poi.longitude == 120.1536
    assert payload.poi.latitude == 30.2875
    assert payload.poi.ticket_price == 80.0


def test_list_items_with_poi_rejects_non_owner():
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=uuid4())
    user = SimpleNamespace(id=uuid4())

    db = SimpleNamespace()
    db.get = lambda model, entity_id: itinerary

    with pytest.raises(HTTPException) as exc_info:
        list_items_with_poi(db, itinerary_id, user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Itinerary not found"

