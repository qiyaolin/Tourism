from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import block_templates as block_templates_api
from app.api.v1 import blocks as blocks_api
from app.db.session import get_db
from app.security.deps import get_current_user


@pytest.fixture
def fake_db():
    return object()


@pytest.fixture
def app(fake_db):
    api = FastAPI()
    api.include_router(blocks_api.router, prefix="/api/v1")
    api.include_router(block_templates_api.router, prefix="/api/v1")
    api.dependency_overrides[get_db] = lambda: fake_db
    api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user", nickname="tester", created_at=datetime.now(UTC)
    )
    yield api
    api.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


def test_get_blocks_api_returns_tree(client, fake_db, monkeypatch):
    itinerary_id = uuid4()
    block_id = uuid4()
    now = datetime.now(UTC)
    seen = {}

    def _fake_list_block_tree(db, actual_itinerary_id):
        seen["db"] = db
        seen["itinerary_id"] = actual_itinerary_id
        return [
            {
                "id": block_id,
                "itinerary_id": itinerary_id,
                "parent_block_id": None,
                "sort_order": 1,
                "day_index": 1,
                "lane_key": "core",
                "start_minute": 540,
                "end_minute": 660,
                "block_type": "scenic",
                "title": "West Lake",
                "duration_minutes": 120,
                "cost": 0.0,
                "tips": None,
                "longitude": None,
                "latitude": None,
                "address": "Hangzhou",
                "photos": None,
                "type_data": None,
                "is_container": False,
                "source_template_id": None,
                "status": "draft",
                "priority": "medium",
                "risk_level": "low",
                "assignee_user_id": None,
                "tags": ["hangzhou"],
                "ui_meta": {"collapsed": False},
                "children": [],
                "created_at": now,
                "updated_at": now,
            }
        ]

    monkeypatch.setattr(blocks_api.block_service, "list_block_tree", _fake_list_block_tree)

    response = client.get(f"/api/v1/itineraries/{itinerary_id}/blocks")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(block_id)
    assert seen["db"] is fake_db
    assert str(seen["itinerary_id"]) == str(itinerary_id)


def test_list_templates_api_returns_service_result(client, fake_db, monkeypatch):
    template_id = uuid4()
    author_id = uuid4()
    now = datetime.now(UTC)
    seen = {}

    def _fake_list_templates(db, **kwargs):
        seen["db"] = db
        seen["kwargs"] = kwargs
        return (
            [
                {
                    "id": template_id,
                    "author_id": author_id,
                    "author_nickname": "alice",
                    "title": "One Day City Walk",
                    "description": "sample",
                    "style_tags": ["city"],
                    "block_type": "scenic",
                    "is_group": False,
                    "content_snapshot": {"duration_minutes": 90},
                    "children_snapshot": None,
                    "fork_count": 3,
                    "rating_avg": 4.8,
                    "rating_count": 5,
                    "status": "published",
                    "region_name": "Hangzhou",
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            1,
        )

    monkeypatch.setattr(
        block_templates_api.block_template_service,
        "list_templates",
        _fake_list_templates,
    )

    response = client.get("/api/v1/templates?sort_by=hot&offset=0&limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(template_id)
    assert seen["db"] is fake_db
    assert seen["kwargs"]["sort_by"] == "hot"


def test_get_board_api_returns_summary(client, fake_db, monkeypatch):
    itinerary_id = uuid4()
    block_id = uuid4()
    edge_id = uuid4()
    now = datetime.now(UTC)

    def _fake_list_board(db, actual_itinerary_id):
        assert db is fake_db
        assert str(actual_itinerary_id) == str(itinerary_id)
        return {
            "itinerary_id": itinerary_id,
            "items": [
                {
                    "id": block_id,
                    "itinerary_id": itinerary_id,
                    "parent_block_id": None,
                    "sort_order": 1,
                    "day_index": 1,
                    "lane_key": "core",
                    "start_minute": 540,
                    "end_minute": 600,
                    "block_type": "scenic",
                    "title": "West Lake",
                    "duration_minutes": 60,
                    "cost": None,
                    "tips": None,
                    "longitude": None,
                    "latitude": None,
                    "address": None,
                    "photos": None,
                    "type_data": None,
                    "is_container": False,
                    "source_template_id": None,
                    "status": "ready",
                    "priority": "high",
                    "risk_level": "low",
                    "assignee_user_id": None,
                    "tags": None,
                    "ui_meta": None,
                    "children": [],
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            "dependencies": [
                {
                    "id": edge_id,
                    "itinerary_id": itinerary_id,
                    "from_block_id": block_id,
                    "to_block_id": block_id,
                    "edge_type": "soft",
                    "created_at": now,
                }
            ],
            "lanes": [{"lane_key": "core", "label": "核心流程", "block_count": 1, "done_count": 0}],
            "summary": {"block_count": 1, "dependency_count": 1, "blocked_count": 0},
        }

    monkeypatch.setattr(blocks_api.block_service, "list_board", _fake_list_board)
    response = client.get(f"/api/v1/itineraries/{itinerary_id}/board")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["dependency_count"] == 1
    assert body["lanes"][0]["lane_key"] == "core"


def test_update_block_layout_api_calls_service(client, monkeypatch):
    block_id = uuid4()
    itinerary_id = uuid4()
    now = datetime.now(UTC)
    seen = {}

    def _fake_update_block_layout(db, actual_block_id, payload):
        seen["block_id"] = actual_block_id
        seen["payload"] = payload
        return {
            "id": actual_block_id,
            "itinerary_id": itinerary_id,
            "parent_block_id": None,
            "sort_order": 2,
            "day_index": 2,
            "lane_key": "dining",
            "start_minute": 720,
            "end_minute": 810,
            "block_type": "dining",
            "title": "Lunch",
            "duration_minutes": 90,
            "cost": 88.0,
            "tips": None,
            "longitude": None,
            "latitude": None,
            "address": None,
            "photos": None,
            "type_data": None,
            "is_container": False,
            "source_template_id": None,
            "status": "running",
            "priority": "medium",
            "risk_level": "low",
            "assignee_user_id": None,
            "tags": ["meal"],
            "ui_meta": None,
            "children": [],
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(blocks_api.block_service, "update_block_layout", _fake_update_block_layout)
    response = client.patch(
        f"/api/v1/itineraries/blocks/{block_id}/layout",
        json={"day_index": 2, "lane_key": "dining", "start_minute": 720, "end_minute": 810},
    )
    assert response.status_code == 200
    assert str(seen["block_id"]) == str(block_id)
    assert seen["payload"].lane_key == "dining"
