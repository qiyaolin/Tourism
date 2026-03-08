from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import admin_territories as admin_territories_api
from app.api.v1 import territories as territories_api
from app.db.session import get_db
from app.schemas.territory import (
    TaskCenterItem,
    TaskCenterResponse,
    TerritoryGuardianApplicationListResponse,
    TerritoryGuardianApplicationResponse,
    TerritoryGuardianBrief,
    TerritoryGuardianCheckInResponse,
    TerritoryOpportunityResponse,
    TerritoryRebuildResponse,
    TerritoryRegionItem,
    TerritoryRegionListResponse,
    UserTerritoryProfileResponse,
    UserTerritoryRoleItem,
)
from app.security.deps import get_current_user, require_admin


@pytest.fixture
def fake_db():
    return object()


@pytest.fixture
def app(fake_db):
    api = FastAPI()
    api.include_router(territories_api.router, prefix="/api/v1")
    api.include_router(admin_territories_api.router, prefix="/api/v1")
    api.dependency_overrides[get_db] = lambda: fake_db
    api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user", nickname="tester"
    )
    api.dependency_overrides[require_admin] = lambda: SimpleNamespace(
        id=uuid4(), role="admin", nickname="admin"
    )
    yield api
    api.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


def _sample_region(territory_id):
    now = datetime.now(UTC)
    return TerritoryRegionItem(
        id=territory_id,
        code="cell_1_1",
        name="Region A",
        status="active",
        poi_count=3,
        boundary_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
        centroid_wkt="POINT(0.5 0.5)",
        guardians=[
            TerritoryGuardianBrief(
                user_id=uuid4(),
                nickname="guardian",
                role="regular",
                state="active",
                granted_at=now,
            )
        ],
        sample_pois=["POI A"],
    )


def _sample_application(territory_id, application_id):
    now = datetime.now(UTC)
    return TerritoryGuardianApplicationResponse(
        id=application_id,
        territory_id=territory_id,
        territory_name="Region A",
        applicant_user_id=uuid4(),
        applicant_nickname="alice",
        reason="help",
        status="pending",
        reviewer_user_id=None,
        reviewer_nickname=None,
        review_comment=None,
        reviewed_at=None,
        created_at=now,
    )


def test_list_territories_api_returns_service_result(client, fake_db, monkeypatch):
    territory_id = uuid4()
    expected = TerritoryRegionListResponse(items=[_sample_region(territory_id)])
    seen = {}

    def _fake_list_territories(db):
        seen["db"] = db
        return expected

    monkeypatch.setattr(territories_api, "list_territories", _fake_list_territories)

    response = client.get("/api/v1/territories")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(territory_id)
    assert seen["db"] is fake_db


def test_get_my_profile_api_returns_service_result(client, fake_db, monkeypatch):
    user_id = uuid4()
    expected = UserTerritoryProfileResponse(
        user_id=user_id,
        roles=[
            UserTerritoryRoleItem(
                territory_id=uuid4(),
                territory_name="Region A",
                role="regular",
                state="active",
                contribution_count=5,
                thanks_received=1,
                next_role="local_expert",
                next_role_progress=0.5,
            )
        ],
        total_contributions=5,
        total_thanks=1,
    )
    seen = {}

    def _fake_profile(db, route_user_id):
        seen["db"] = db
        seen["user_id"] = route_user_id
        return expected

    monkeypatch.setattr(territories_api, "get_user_territory_profile", _fake_profile)
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id, role="user", nickname="tester"
    )

    response = client.get("/api/v1/territories/me/profile")

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user_id)
    assert seen["db"] is fake_db
    assert seen["user_id"] == user_id


def test_get_my_tasks_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    now = datetime.now(UTC)
    expected = TaskCenterResponse(
        pending_reviews=1,
        items=[
            TaskCenterItem(
                task_type="pending_review",
                title="Review correction: POI A",
                territory_name="Region A",
                territory_id=territory_id,
                target_id=uuid4(),
                points=10,
                created_at=now,
            )
        ],
        monthly_contributions=3,
        monthly_helped_count=2,
    )

    monkeypatch.setattr(territories_api, "get_task_center", lambda _db, _uid: expected)

    response = client.get("/api/v1/territories/me/tasks")

    assert response.status_code == 200
    assert response.json()["pending_reviews"] == 1
    assert response.json()["items"][0]["task_type"] == "pending_review"


def test_get_territory_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    expected = _sample_region(territory_id)

    monkeypatch.setattr(territories_api, "get_territory", lambda _db, _tid: expected)

    response = client.get(f"/api/v1/territories/{territory_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(territory_id)


def test_get_territory_opportunities_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    now = datetime.now(UTC)
    expected = TerritoryOpportunityResponse(
        territory_id=territory_id,
        items=[
            TaskCenterItem(
                task_type="nearby_opportunity",
                title="Update opening hours",
                territory_name="Region A",
                territory_id=territory_id,
                target_id=uuid4(),
                points=10,
                created_at=now,
            )
        ],
    )

    monkeypatch.setattr(territories_api, "get_territory_opportunities", lambda _db, _tid: expected)

    response = client.get(f"/api/v1/territories/{territory_id}/opportunities")

    assert response.status_code == 200
    assert response.json()["territory_id"] == str(territory_id)


def test_submit_guardian_application_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    application_id = uuid4()
    expected = _sample_application(territory_id, application_id)

    monkeypatch.setattr(territories_api, "submit_guardian_application", lambda _db, _payload, _user: expected)

    response = client.post(
        "/api/v1/territories/applications",
        json={"territory_id": str(territory_id), "reason": "help"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(application_id)


def test_guardian_check_in_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    user_id = uuid4()
    now = datetime.now(UTC)
    expected = TerritoryGuardianCheckInResponse(
        territory_id=territory_id,
        guardian_user_id=user_id,
        checked_in_at=now,
    )

    monkeypatch.setattr(territories_api, "guardian_check_in", lambda _db, _tid, _user: expected)

    response = client.post(f"/api/v1/territories/{territory_id}/check-in")

    assert response.status_code == 200
    assert response.json()["territory_id"] == str(territory_id)
    assert response.json()["guardian_user_id"] == str(user_id)


def test_admin_list_guardian_applications_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    application_id = uuid4()
    expected = TerritoryGuardianApplicationListResponse(
        items=[_sample_application(territory_id, application_id)],
        total=1,
        offset=0,
        limit=20,
    )

    monkeypatch.setattr(
        admin_territories_api,
        "list_guardian_applications",
        lambda _db, _status, _offset, _limit: expected,
    )

    response = client.get("/api/v1/admin/territories/applications?status=pending&offset=0&limit=20")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(application_id)


def test_admin_list_guardian_applications_api_rejects_invalid_status(client):
    response = client.get("/api/v1/admin/territories/applications?status=bad")

    assert response.status_code == 422


def test_admin_review_guardian_application_api_returns_service_result(client, monkeypatch):
    territory_id = uuid4()
    application_id = uuid4()
    expected = _sample_application(territory_id, application_id)

    monkeypatch.setattr(
        admin_territories_api,
        "review_guardian_application",
        lambda _db, application_id, action, review_comment, current_user: expected,
    )

    response = client.post(
        f"/api/v1/admin/territories/applications/{application_id}/review",
        json={"action": "approve", "review_comment": "ok"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(application_id)


def test_admin_rebuild_territories_api_returns_service_result(client, monkeypatch):
    expected = TerritoryRebuildResponse(generated_regions=2, assigned_pois=8, inactive_regions=1)

    monkeypatch.setattr(admin_territories_api, "rebuild_territory_regions", lambda _db: expected)

    response = client.post("/api/v1/admin/territories/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "generated_regions": 2,
        "assigned_pois": 8,
        "inactive_regions": 1,
    }
