from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.models.poi import Poi
from app.schemas.ai_engine import (
    AiImportRequest,
    AiPreviewPoi,
    AiPreviewRequest,
    AiPreviewResponse,
)
from app.services.ai_engine_service import (
    _AiRawItem,
    _AiRawResponse,
    _call_llm,
    _place_has_grounding,
    import_ai_plan,
    preview_ai_plan,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, itinerary, user_id):
        self.itinerary = itinerary
        self.user_id = user_id
        self.poi_map = {}
        self.rows = []
        self.added = []
        self.committed = False

    def get(self, model, entity_id):
        if model is Itinerary and entity_id == self.itinerary.id:
            return self.itinerary
        if model is Poi:
            return self.poi_map.get(entity_id)
        return None

    def execute(self, _stmt):
        return _RowsResult(self.rows)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        self.committed = True


def test_preview_ai_plan_reorders_by_day(monkeypatch):
    owner_id = uuid4()
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id, days=3)
    db = _FakeDb(itinerary, owner_id)
    user = SimpleNamespace(id=owner_id)

    def fake_call(_raw_text):
        return _AiRawResponse(
            title="成都三日",
            destination="成都",
            days=2,
            items=[
                _AiRawItem(day_index=2, name="宽窄巷子"),
                _AiRawItem(day_index=1, name="春熙路"),
                _AiRawItem(day_index=2, name="杜甫草堂"),
            ],
        )

    def fake_local(_db, name):
        if name == "春熙路":
            return AiPreviewPoi(
                poi_id=uuid4(),
                name="春熙路",
                type="shopping",
                longitude=104.0817,
                latitude=30.6571,
                match_source="local",
            )
        return None

    def fake_amap(name, _destination, _fallback_type):
        return AiPreviewPoi(
            name=name,
            type="scenic",
            longitude=104.0,
            latitude=30.0,
            match_source="amap",
        )

    monkeypatch.setattr("app.services.ai_engine_service._call_llm", fake_call)
    monkeypatch.setattr("app.services.ai_engine_service._resolve_local_poi", fake_local)
    monkeypatch.setattr("app.services.ai_engine_service._resolve_amap_poi", fake_amap)

    result = preview_ai_plan(
        db,
        AiPreviewRequest(
            raw_text="第一天去春熙路，第二天去宽窄巷子和杜甫草堂。",
            itinerary_id=itinerary_id,
        ),
        user,
    )

    assert isinstance(result, AiPreviewResponse)
    assert [item.day_index for item in result.items] == [1, 2, 2]
    assert [item.sort_order for item in result.items] == [1, 1, 2]
    assert result.days == 2


def test_import_ai_plan_appends_sort_order():
    owner_id = uuid4()
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id, days=3, status="draft")
    db = _FakeDb(itinerary, owner_id)
    user = SimpleNamespace(id=owner_id)

    existing_day1_max = 2
    db.rows = [(1, existing_day1_max)]
    poi_a = SimpleNamespace(id=uuid4())
    poi_b = SimpleNamespace(id=uuid4())
    db.poi_map = {poi_a.id: poi_a, poi_b.id: poi_b}

    preview = AiPreviewResponse(
        title="测试行程",
        destination="北京",
        days=3,
        items=[
            {
                "day_index": 1,
                "sort_order": 1,
                "start_time": "09:00",
                "duration_minutes": 60,
                "cost": 0,
                "tips": None,
                "poi": {
                    "poi_id": poi_a.id,
                    "name": "A",
                    "type": "scenic",
                    "match_source": "local",
                },
            },
            {
                "day_index": 2,
                "sort_order": 1,
                "start_time": None,
                "duration_minutes": None,
                "cost": None,
                "tips": None,
                "poi": {
                    "poi_id": poi_b.id,
                    "name": "B",
                    "type": "scenic",
                    "match_source": "local",
                },
            },
        ],
    )

    response = import_ai_plan(db, AiImportRequest(itinerary_id=itinerary_id, preview=preview), user)

    added_items = [item for item in db.added if isinstance(item, ItineraryItem)]
    assert response.imported_count == 2
    assert db.committed is True
    assert [item.day_index for item in added_items] == [1, 2]
    assert [item.sort_order for item in added_items] == [3, 1]
    assert itinerary.status == "in_progress"


def test_import_ai_plan_rejects_unresolved_poi():
    owner_id = uuid4()
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id, days=2, status="draft")
    db = _FakeDb(itinerary, owner_id)
    user = SimpleNamespace(id=owner_id)

    preview = AiPreviewResponse(
        title="测试",
        destination="成都",
        days=2,
        items=[
            {
                "day_index": 1,
                "sort_order": 1,
                "start_time": None,
                "duration_minutes": None,
                "cost": None,
                "tips": None,
                "poi": {
                    "name": "未知地点",
                    "type": "scenic",
                    "match_source": "unresolved",
                },
            }
        ],
    )

    with pytest.raises(HTTPException) as exc:
        import_ai_plan(db, AiImportRequest(itinerary_id=itinerary_id, preview=preview), user)

    assert exc.value.status_code == 400


def test_call_llm_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setattr("app.services.ai_engine_service.settings.ai_provider", "gemini")

    def fake_call(_raw_text):
        return _AiRawResponse(
            title="测试",
            destination="北京",
            days=1,
            items=[_AiRawItem(day_index=1, name="天安门")],
        )

    monkeypatch.setattr("app.services.ai_engine_service._call_gemini", fake_call)
    result = _call_llm("input")
    assert result.destination == "北京"


def test_call_llm_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr("app.services.ai_engine_service.settings.ai_provider", "unknown")
    with pytest.raises(HTTPException) as exc:
        _call_llm("input")
    assert exc.value.status_code == 503


def test_preview_ai_plan_returns_structured_422_when_items_empty(monkeypatch):
    owner_id = uuid4()
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id, days=2)
    db = _FakeDb(itinerary, owner_id)
    user = SimpleNamespace(id=owner_id)

    def fake_call(_raw_text):
        return _AiRawResponse(title="空", destination="北京", days=1, items=[])

    monkeypatch.setattr("app.services.ai_engine_service._call_llm", fake_call)

    with pytest.raises(HTTPException) as exc:
        request = AiPreviewRequest(raw_text="只有一句话", itinerary_id=itinerary_id)
        preview_ai_plan(db, request, user)

    assert exc.value.status_code == 422
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail["error_code"] == "AI_EMPTY_ITEMS"


def test_preview_ai_plan_returns_422_when_items_have_no_grounding(monkeypatch):
    owner_id = uuid4()
    itinerary_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id, days=2)
    db = _FakeDb(itinerary, owner_id)
    user = SimpleNamespace(id=owner_id)

    def fake_call(_raw_text):
        return _AiRawResponse(
            title="北京随便逛",
            destination="北京",
            days=1,
            items=[
                _AiRawItem(day_index=1, name="老北京风情街"),
                _AiRawItem(day_index=1, name="烟袋斜街"),
            ],
        )

    monkeypatch.setattr("app.services.ai_engine_service._call_llm", fake_call)

    with pytest.raises(HTTPException) as exc:
        request = AiPreviewRequest(
            raw_text="这次就随便逛逛北京吧，时间看情况安排。",
            itinerary_id=itinerary_id,
        )
        preview_ai_plan(db, request, user)

    assert exc.value.status_code == 422
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail["error_code"] == "AI_UNGROUNDED_ITEMS"


def test_place_grounding_with_exact_and_partial_match():
    assert _place_has_grounding("天安门广场", "第一天去天安门广场看升旗")
    assert _place_has_grounding("北京大栅栏", "晚上想去大栅栏吃点东西")
    assert not _place_has_grounding("烟袋斜街", "这次就随便逛逛北京吧")
