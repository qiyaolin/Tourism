from datetime import UTC, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import itinerary_service
from app.services.itinerary_service import (
    get_public_itinerary,
    get_public_itinerary_share_meta,
    list_explore_heatmap,
    list_explore_recommendations,
    list_public_items_with_poi,
    list_public_itineraries,
    record_public_itinerary_view,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def test_list_public_itineraries_returns_author_nickname_and_fork_count(monkeypatch):
    itinerary = SimpleNamespace(
        id=uuid4(),
        title="Beijing Weekend",
        destination="Beijing",
        days=2,
        status="published",
        visibility="public",
        cover_image_url="https://example.com/cover.jpg",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = SimpleNamespace()
    db.scalar = lambda _stmt: 1
    monkeypatch.setattr(
        itinerary_service,
        "_list_public_itinerary_rows_with_metrics",
        lambda _db, **_kwargs: [(itinerary, "alice", 3, 8, None)],
    )

    result = list_public_itineraries(db, 0, 20)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].author_nickname == "alice"
    assert result.items[0].forked_count == 3
    assert result.items[0].cover_image_url == "https://example.com/cover.jpg"


def test_get_public_itinerary_not_found():
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([])

    with pytest.raises(HTTPException) as exc_info:
        get_public_itinerary(db, uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Itinerary not found"


def test_get_public_itinerary_returns_forked_count(monkeypatch):
    itinerary = SimpleNamespace(
        id=uuid4(),
        title="Beijing Weekend",
        destination="Beijing",
        days=2,
        status="published",
        visibility="public",
        cover_image_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([(itinerary, "alice")])
    monkeypatch.setattr(itinerary_service, "_get_forked_count_map", lambda _db, _ids: {itinerary.id: 5})
    monkeypatch.setattr(itinerary_service, "_get_last_viewed_map", lambda _db, _ids: {})

    result = get_public_itinerary(db, itinerary.id)

    assert result.author_nickname == "alice"
    assert result.forked_count == 5


def test_get_public_itinerary_share_meta_returns_share_fields(monkeypatch):
    itinerary = SimpleNamespace(
        id=uuid4(),
        title="Beijing Weekend",
        destination="Beijing",
        days=2,
        status="published",
        visibility="public",
        cover_image_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([(itinerary, "alice")])
    monkeypatch.setattr(itinerary_service.settings, "itinerary_share_base_url", "http://localhost:5173/itineraries")
    monkeypatch.setattr(itinerary_service.settings, "share_og_base_url", "http://localhost:8000/share/itineraries")
    monkeypatch.setattr(itinerary_service.settings, "share_default_cover_url", "https://example.com/default-cover.jpg")

    result = get_public_itinerary_share_meta(db, itinerary.id)

    assert result.itinerary_id == itinerary.id
    assert result.description == "Beijing · 2 天 · 作者 alice"
    assert result.cover_image_url == "https://example.com/default-cover.jpg"
    assert result.public_url.endswith(str(itinerary.id))
    assert result.share_card_url.endswith(str(itinerary.id))


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
        tips="avoid rush hour",
    )
    poi = SimpleNamespace(
        id=poi_id,
        name="Temple of Heaven",
        type="sightseeing",
        address="Dongcheng",
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


def test_record_public_itinerary_view_returns_visit_log(monkeypatch):
    itinerary = SimpleNamespace(id=uuid4())
    current_user = SimpleNamespace(id=uuid4())
    now = datetime.now(UTC)
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([(now, 2)])
    db.commit = lambda: None
    monkeypatch.setattr(
        itinerary_service,
        "_ensure_public_itinerary",
        lambda _db, _itinerary_id: (itinerary, "alice"),
    )

    result = record_public_itinerary_view(db, itinerary.id, current_user)

    assert result.itinerary_id == itinerary.id
    assert result.view_count == 2
    assert result.last_viewed_at == now


def test_list_explore_heatmap_returns_ranked_points():
    poi_id = uuid4()
    db = SimpleNamespace()
    db.execute = lambda _stmt: _RowsResult([(poi_id, "Temple of Heaven", "POINT(116.4105 39.8812)", 9)])

    result = list_explore_heatmap(db, 10)

    assert len(result.items) == 1
    assert result.items[0].poi_id == poi_id
    assert result.items[0].heat_score == 9
    assert result.items[0].name == "Temple of Heaven"


def test_list_explore_recommendations_falls_back_to_popularity(monkeypatch):
    itinerary = SimpleNamespace(
        id=uuid4(),
        title="Beijing Highlights",
        destination="Beijing",
        days=2,
        status="published",
        visibility="public",
        cover_image_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = SimpleNamespace()
    monkeypatch.setattr(
        itinerary_service,
        "_list_public_itinerary_rows_with_metrics",
        lambda _db, **_kwargs: [(itinerary, "alice", 4, 7, None)],
    )
    monkeypatch.setattr(
        itinerary_service,
        "_sort_public_rows_by_popularity",
        lambda rows: rows,
    )

    result = list_explore_recommendations(db, None, 6)

    assert len(result.items) == 1
    assert result.items[0].itinerary.id == itinerary.id
    assert result.items[0].score == 11
    assert "被借鉴 4 次" in result.items[0].reasons


def test_list_explore_recommendations_prefers_matching_type(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    itinerary_match = SimpleNamespace(
        id=uuid4(),
        title="Museum Route",
        destination="Beijing",
        days=1,
        status="published",
        visibility="public",
        cover_image_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    itinerary_plain = SimpleNamespace(
        id=uuid4(),
        title="Park Route",
        destination="Beijing",
        days=1,
        status="published",
        visibility="public",
        cover_image_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    rows = [
        (itinerary_plain, "bob", 1, 0, None),
        (itinerary_match, "alice", 0, 0, None),
    ]
    db = SimpleNamespace()
    monkeypatch.setattr(itinerary_service, "_get_viewed_itinerary_ids", lambda _db, _user_id: set())
    monkeypatch.setattr(itinerary_service, "_get_user_preferred_poi_types", lambda _db, _user_id: {"museum": 3})
    monkeypatch.setattr(itinerary_service, "_list_public_itinerary_rows_with_metrics", lambda _db, **_kwargs: rows)
    monkeypatch.setattr(
        itinerary_service,
        "_get_itinerary_poi_type_count_map",
        lambda _db, _ids: {
            itinerary_match.id: {"museum": 2},
            itinerary_plain.id: {"park": 2},
        },
    )

    result = list_explore_recommendations(db, user, 2)

    assert result.items[0].itinerary.id == itinerary_match.id
    assert any(reason.startswith("偏好匹配：") for reason in result.items[0].reasons)
