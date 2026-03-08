from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import admin_bounties as admin_bounties_api
from app.api.v1 import bounties as bounties_api
from app.db.session import get_db
from app.schemas.bounty import (
    BountySubmissionItem,
    BountySubmissionListResponse,
    BountySubmitResponse,
    BountyTaskItem,
    BountyTaskListResponse,
)
from app.security.deps import get_current_user, require_admin


@pytest.fixture
def fake_db():
    return object()


@pytest.fixture
def app(fake_db):
    api = FastAPI()
    api.include_router(bounties_api.router, prefix="/api/v1")
    api.include_router(admin_bounties_api.router, prefix="/api/v1")
    api.dependency_overrides[get_db] = lambda: fake_db
    api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user", nickname="tester", created_at=datetime.now(UTC)
    )
    api.dependency_overrides[require_admin] = lambda: SimpleNamespace(
        id=uuid4(), role="admin", nickname="admin", created_at=datetime.now(UTC)
    )
    yield api
    api.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


def _sample_task_item(task_id):
    return BountyTaskItem(
        id=task_id,
        poi_id=uuid4(),
        poi_name="POI A",
        territory_id=uuid4(),
        territory_name="Region A",
        status="open",
        reward_points=20,
        stale_days_snapshot=45,
        distance_meters=123.4,
        generated_at=datetime.now(UTC),
        expires_at=None,
        claimed_by_user_id=None,
        claimed_at=None,
    )


def _sample_submission_item(submission_id, task_id):
    return BountySubmissionItem(
        id=submission_id,
        task_id=task_id,
        submitter_user_id=uuid4(),
        submit_longitude=104.1,
        submit_latitude=30.6,
        distance_meters=120.2,
        gps_verified=True,
        photo_url="/uploads/2026/02/x.jpg",
        photo_exif_captured_at=datetime.now(UTC),
        photo_exif_longitude=104.1,
        photo_exif_latitude=30.6,
        risk_level="normal",
        review_status="approved",
        reviewer_user_id=None,
        review_comment=None,
        reviewed_at=None,
        created_at=datetime.now(UTC),
        task_status="approved",
        poi_name="POI A",
        territory_name="Region A",
        reward_points=20,
    )


def test_list_bounty_tasks_api_returns_service_result(client, fake_db, monkeypatch):
    task_id = uuid4()
    expected = BountyTaskListResponse(
        items=[_sample_task_item(task_id)],
        total=1,
        offset=0,
        limit=20,
        nearby_radius_meters=None,
    )
    seen = {}

    def _fake_list_bounty_tasks(db, current_user, **kwargs):
        seen["db"] = db
        seen["scope"] = kwargs["scope"]
        return expected

    monkeypatch.setattr(bounties_api, "list_bounty_tasks", _fake_list_bounty_tasks)

    response = client.get("/api/v1/bounties?scope=all&offset=0&limit=20")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(task_id)
    assert seen["db"] is fake_db
    assert seen["scope"] == "all"


def test_claim_bounty_task_api_returns_service_result(client, monkeypatch):
    task_id = uuid4()
    expected = _sample_task_item(task_id)
    expected.status = "claimed"
    expected.claimed_by_user_id = uuid4()
    expected.claimed_at = datetime.now(UTC)
    monkeypatch.setattr(bounties_api, "claim_bounty_task", lambda _db, _task_id, _user: expected)

    response = client.post(f"/api/v1/bounties/{task_id}/claim")

    assert response.status_code == 200
    assert response.json()["status"] == "claimed"


def test_submit_bounty_task_api_returns_service_result(client, monkeypatch):
    task_id = uuid4()
    submission_id = uuid4()
    expected = BountySubmitResponse(
        task=_sample_task_item(task_id),
        submission=_sample_submission_item(submission_id, task_id),
        auto_approved=True,
    )
    async def _fake_submit_bounty_task(**_kwargs):
        return expected

    monkeypatch.setattr(bounties_api, "submit_bounty_task", _fake_submit_bounty_task)

    response = client.post(
        f"/api/v1/bounties/{task_id}/submit",
        files={"photo": ("photo.jpg", BytesIO(b"image-bytes"), "image/jpeg")},
        data={"submit_longitude": "104.1", "submit_latitude": "30.6", "details": "现场核验"},
    )

    assert response.status_code == 200
    assert response.json()["auto_approved"] is True
    assert response.json()["submission"]["id"] == str(submission_id)


def test_list_my_bounty_submissions_api_returns_service_result(client, monkeypatch):
    task_id = uuid4()
    submission_id = uuid4()
    expected = BountySubmissionListResponse(
        items=[_sample_submission_item(submission_id, task_id)],
        total=1,
        offset=0,
        limit=20,
    )
    monkeypatch.setattr(
        bounties_api,
        "list_my_bounty_submissions",
        lambda _db, _user, offset, limit: expected,
    )

    response = client.get("/api/v1/bounties/mine/submissions")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(submission_id)


def test_admin_list_bounty_submissions_api_returns_service_result(client, monkeypatch):
    task_id = uuid4()
    submission_id = uuid4()
    expected = BountySubmissionListResponse(
        items=[_sample_submission_item(submission_id, task_id)],
        total=1,
        offset=0,
        limit=20,
    )
    monkeypatch.setattr(
        admin_bounties_api,
        "list_admin_bounty_submissions",
        lambda _db, review_status_filter, offset, limit: expected,
    )

    response = client.get("/api/v1/admin/bounties/submissions?status=pending&offset=0&limit=20")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(submission_id)


def test_admin_review_bounty_submission_api_returns_service_result(client, monkeypatch):
    task_id = uuid4()
    submission_id = uuid4()
    expected = _sample_submission_item(submission_id, task_id)
    expected.review_status = "approved"
    monkeypatch.setattr(admin_bounties_api, "review_bounty_submission", lambda _db, **_kwargs: expected)

    response = client.post(
        f"/api/v1/admin/bounties/submissions/{submission_id}/review",
        json={"action": "approve", "review_comment": "ok"},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"
