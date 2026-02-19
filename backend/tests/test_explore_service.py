from datetime import UTC, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.itinerary_service import (
    get_public_itinerary,
    list_public_items_with_poi,
    list_public_itineraries,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def test_list_public_itineraries_returns_author_nickname():
    itinerary = SimpleNamespace(
        id=uuid4(),
        title="北京周末",
        destination="北京",
        days=2,
        status="published",
        visibility="public",
        cover_image_url="https://example.com/cover.jpg",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = SimpleNamespace()
    db.scalar = lambda _stmt: 1
    db.execute = lambda _stmt: _RowsResult([(itinerary, "小王")])

    result = list_public_itineraries(db, 0, 20)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].author_nickname == "小王"
    assert result.items[0].cover_image_url == "https://example.com/cover.jpg"


def test_get_public_itinerary_not_found():
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([])

    with pytest.raises(HTTPException) as exc_info:
        get_public_itinerary(db, uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Itinerary not found"


def test_list_public_items_with_poi_rejects_non_public_itinerary():
    itinerary = SimpleNamespace(id=uuid4(), status="draft", visibility="private")
    db = SimpleNamespace()
    db.get = lambda _model, _id: itinerary

    with pytest.raises(HTTPException) as exc_info:
        list_public_items_with_poi(db, itinerary.id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Itinerary not found"


def test_list_public_items_with_poi_returns_items():
    itinerary_id = uuid4()
    item_id = uuid4()
    poi_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, status="published", visibility="public")
    item = SimpleNamespace(
        id=item_id,
        itinerary_id=itinerary_id,
        day_index=1,
        sort_order=1,
        start_time=time(hour=9, minute=0),
        duration_minutes=60,
        cost=Decimal("88.00"),
        tips="避开高峰",
    )
    poi = SimpleNamespace(
        id=poi_id,
        name="天坛",
        type="sightseeing",
        address="东城区",
        opening_hours="09:00-17:00",
        ticket_price=Decimal("15.00"),
    )
    db = SimpleNamespace()
    db.get = lambda _model, _id: itinerary
    db.execute = lambda _stmt: _RowsResult([(item, poi, "POINT(116.4105 39.8812)")])

    result = list_public_items_with_poi(db, itinerary_id)

    assert len(result.items) == 1
    assert result.items[0].item_id == item_id
    assert result.items[0].poi.id == poi_id
