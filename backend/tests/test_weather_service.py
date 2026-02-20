from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.itinerary import Itinerary
from app.services import weather_service
from app.services.weather_service import get_itinerary_weather


class _FakeDb:
    def __init__(self, itinerary):
        self.itinerary = itinerary

    def get(self, model, entity_id):
        if model is Itinerary and self.itinerary and self.itinerary.id == entity_id:
            return self.itinerary
        return None


@pytest.fixture(autouse=True)
def _clear_cache():
    weather_service._weather_cache.clear()
    yield
    weather_service._weather_cache.clear()


def test_get_itinerary_weather_returns_mapped_days(monkeypatch):
    owner_id = uuid4()
    itinerary = SimpleNamespace(
        id=uuid4(),
        creator_user_id=owner_id,
        destination="上海",
        start_date=date(2026, 2, 20),
        days=3,
    )
    db = _FakeDb(itinerary)
    current_user = SimpleNamespace(id=owner_id)

    monkeypatch.setattr("app.services.weather_service._lookup_location_id", lambda _client, _dest: "101")
    monkeypatch.setattr(
        "app.services.weather_service._fetch_7d_weather",
        lambda _client, _location: [
            {"fxDate": "2026-02-20", "textDay": "晴", "iconDay": "100", "tempMin": "8", "tempMax": "15"},
            {"fxDate": "2026-02-21", "textDay": "多云", "iconDay": "101", "tempMin": "9", "tempMax": "16"},
            {"fxDate": "2026-02-22", "textDay": "小雨", "iconDay": "305", "tempMin": "7", "tempMax": "12"},
        ],
    )

    result = get_itinerary_weather(db, itinerary.id, current_user)

    assert result.itinerary_id == itinerary.id
    assert len(result.items) == 3
    assert result.items[0].text == "晴"
    assert result.items[1].temp_max == 16
    assert result.items[2].date.isoformat() == "2026-02-22"


def test_get_itinerary_weather_requires_start_date():
    owner_id = uuid4()
    itinerary = SimpleNamespace(
        id=uuid4(),
        creator_user_id=owner_id,
        destination="北京",
        start_date=None,
        days=2,
    )
    db = _FakeDb(itinerary)

    with pytest.raises(HTTPException) as exc:
        get_itinerary_weather(db, itinerary.id, SimpleNamespace(id=owner_id))

    assert exc.value.status_code == 400


def test_get_itinerary_weather_uses_cache_and_force_refresh(monkeypatch):
    owner_id = uuid4()
    itinerary = SimpleNamespace(
        id=uuid4(),
        creator_user_id=owner_id,
        destination="成都",
        start_date=date(2026, 2, 20),
        days=2,
    )
    db = _FakeDb(itinerary)
    calls = {"count": 0}

    monkeypatch.setattr("app.services.weather_service._lookup_location_id", lambda _client, _dest: "201")

    def _stub_fetch(_client, _location):
        calls["count"] += 1
        return [
            {"fxDate": "2026-02-20", "textDay": "阴", "iconDay": "104", "tempMin": "6", "tempMax": "13"},
            {"fxDate": "2026-02-21", "textDay": "晴", "iconDay": "100", "tempMin": "5", "tempMax": "14"},
        ]

    monkeypatch.setattr("app.services.weather_service._fetch_7d_weather", _stub_fetch)

    get_itinerary_weather(db, itinerary.id, SimpleNamespace(id=owner_id))
    get_itinerary_weather(db, itinerary.id, SimpleNamespace(id=owner_id))
    assert calls["count"] == 1

    get_itinerary_weather(db, itinerary.id, SimpleNamespace(id=owner_id), force_refresh=True)
    assert calls["count"] == 2
