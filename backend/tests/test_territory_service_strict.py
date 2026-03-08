from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.models.poi import Poi
from app.models.territory import TerritoryGuardian, TerritoryGuardianApplication, TerritoryRegion
from app.models.user import User
from app.schemas.territory import TerritoryGuardianApplicationCreatePayload
from app.services import territory_service


class _ScalarResult:
    def __init__(self, first_value=None, all_value=None):
        self._first_value = first_value
        self._all_value = [] if all_value is None else all_value

    def first(self):
        return self._first_value

    def all(self):
        return self._all_value


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    def __init__(self, *, get_map=None, scalars_results=None, execute_results=None, scalar_results=None):
        self.get_map = {} if get_map is None else dict(get_map)
        self.scalars_results = [] if scalars_results is None else list(scalars_results)
        self.execute_results = [] if execute_results is None else list(execute_results)
        self.scalar_results = [] if scalar_results is None else list(scalar_results)
        self.added = []
        self.commits = 0
        self.refresh_calls = 0

    def get(self, model, entity_id):
        return self.get_map.get((model, entity_id))

    def scalars(self, _stmt):
        if not self.scalars_results:
            raise AssertionError("Unexpected db.scalars call")
        return self.scalars_results.pop(0)

    def execute(self, _stmt):
        if not self.execute_results:
            raise AssertionError("Unexpected db.execute call")
        return self.execute_results.pop(0)

    def scalar(self, _stmt):
        if not self.scalar_results:
            raise AssertionError("Unexpected db.scalar call")
        return self.scalar_results.pop(0)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        self.refresh_calls += 1
        if getattr(value, "id", None) is None:
            value.id = uuid4()
        if getattr(value, "created_at", None) is None:
            value.created_at = datetime.now(UTC)

    def flush(self):
        return None


def test_submit_guardian_application_success():
    territory_id = uuid4()
    user_id = uuid4()
    territory = SimpleNamespace(id=territory_id, status="active", name="Region A")
    current_user = SimpleNamespace(id=user_id, nickname="alice")
    db = _FakeDb(
        get_map={(TerritoryRegion, territory_id): territory},
        scalars_results=[_ScalarResult(first_value=None), _ScalarResult(first_value=None)],
    )
    payload = TerritoryGuardianApplicationCreatePayload(territory_id=territory_id, reason="  I can help  ")

    result = territory_service.submit_guardian_application(db, payload, current_user)

    assert result.status == "pending"
    assert result.reason == "I can help"
    assert result.territory_name == "Region A"
    assert db.commits == 1
    assert db.refresh_calls == 1
    assert any(isinstance(item, TerritoryGuardianApplication) for item in db.added)


def test_submit_guardian_application_rejects_inactive_territory():
    territory_id = uuid4()
    territory = SimpleNamespace(id=territory_id, status="inactive", name="Region A")
    current_user = SimpleNamespace(id=uuid4(), nickname="alice")
    db = _FakeDb(get_map={(TerritoryRegion, territory_id): territory})
    payload = TerritoryGuardianApplicationCreatePayload(territory_id=territory_id, reason="x")

    with pytest.raises(HTTPException) as exc:
        territory_service.submit_guardian_application(db, payload, current_user)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Territory not found"


def test_submit_guardian_application_rejects_existing_guardian():
    territory_id = uuid4()
    territory = SimpleNamespace(id=territory_id, status="active", name="Region A")
    current_user = SimpleNamespace(id=uuid4(), nickname="alice")
    db = _FakeDb(
        get_map={(TerritoryRegion, territory_id): territory},
        scalars_results=[_ScalarResult(first_value=SimpleNamespace(id=uuid4()))],
    )
    payload = TerritoryGuardianApplicationCreatePayload(territory_id=territory_id, reason="x")

    with pytest.raises(HTTPException) as exc:
        territory_service.submit_guardian_application(db, payload, current_user)

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Already a guardian for this territory"


def test_submit_guardian_application_rejects_duplicate_pending():
    territory_id = uuid4()
    territory = SimpleNamespace(id=territory_id, status="active", name="Region A")
    current_user = SimpleNamespace(id=uuid4(), nickname="alice")
    db = _FakeDb(
        get_map={(TerritoryRegion, territory_id): territory},
        scalars_results=[_ScalarResult(first_value=None), _ScalarResult(first_value=SimpleNamespace(id=uuid4()))],
    )
    payload = TerritoryGuardianApplicationCreatePayload(territory_id=territory_id, reason="x")

    with pytest.raises(HTTPException) as exc:
        territory_service.submit_guardian_application(db, payload, current_user)

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Pending application already exists"


def test_review_guardian_application_approve_creates_guardian():
    territory_id = uuid4()
    applicant_id = uuid4()
    reviewer_id = uuid4()
    application = SimpleNamespace(
        id=uuid4(),
        territory_id=territory_id,
        applicant_user_id=applicant_id,
        reason="request",
        status="pending",
        reviewer_user_id=None,
        review_comment=None,
        reviewed_at=None,
        created_at=datetime.now(UTC),
    )
    territory = SimpleNamespace(id=territory_id, name="Region A")
    applicant = SimpleNamespace(id=applicant_id, nickname="alice")
    reviewer = SimpleNamespace(id=reviewer_id, nickname="admin")
    current_user = SimpleNamespace(id=reviewer_id)
    db = _FakeDb(
        get_map={
            (TerritoryRegion, territory_id): territory,
            (User, applicant_id): applicant,
            (User, reviewer_id): reviewer,
        },
        scalars_results=[_ScalarResult(first_value=application), _ScalarResult(first_value=None)],
    )

    result = territory_service.review_guardian_application(
        db,
        application_id=application.id,
        action="approve",
        review_comment="ok",
        current_user=current_user,
    )

    assert result.status == "approved"
    assert result.reviewer_nickname == "admin"
    created_guardians = [item for item in db.added if isinstance(item, TerritoryGuardian)]
    assert len(created_guardians) == 1
    assert created_guardians[0].state == "active"
    assert created_guardians[0].role == "regular"
    assert db.commits == 1


def test_review_guardian_application_rejects_non_pending():
    application = SimpleNamespace(id=uuid4(), status="approved")
    db = _FakeDb(scalars_results=[_ScalarResult(first_value=application)])

    with pytest.raises(HTTPException) as exc:
        territory_service.review_guardian_application(
            db,
            application_id=application.id,
            action="reject",
            review_comment=None,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Application already reviewed"


def test_guardian_check_in_rejects_non_guardian():
    db = _FakeDb(scalars_results=[_ScalarResult(first_value=None)])

    with pytest.raises(HTTPException) as exc:
        territory_service.guardian_check_in(db, uuid4(), SimpleNamespace(id=uuid4()))

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Not a guardian of this territory"


def test_guardian_check_in_reactivates_dormant_guardian():
    territory_id = uuid4()
    user_id = uuid4()
    guardian = SimpleNamespace(
        territory_id=territory_id,
        user_id=user_id,
        state="dormant",
        revoked_at=None,
        last_active_at=datetime.now(UTC) - timedelta(days=100),
    )
    db = _FakeDb(scalars_results=[_ScalarResult(first_value=guardian), _ScalarResult(first_value=guardian)])

    result = territory_service.guardian_check_in(db, territory_id, SimpleNamespace(id=user_id))

    assert result.territory_id == territory_id
    assert result.guardian_user_id == user_id
    assert guardian.state == "active"
    assert guardian.last_active_at is not None
    assert db.commits == 1


def test_evaluate_guardian_governance_marks_dormant_and_recovers(monkeypatch):
    now = datetime.now(UTC)
    old_guardian = SimpleNamespace(
        state="active",
        revoked_at=None,
        last_active_at=now - timedelta(days=120),
        granted_at=now - timedelta(days=200),
    )
    recovering_guardian = SimpleNamespace(
        state="dormant",
        revoked_at=None,
        last_active_at=now - timedelta(days=10),
        granted_at=now - timedelta(days=60),
    )
    db = _FakeDb(scalars_results=[_ScalarResult(all_value=[old_guardian, recovering_guardian])])
    monkeypatch.setattr(territory_service.settings, "guardian_dormant_window_days", 90)

    territory_service.evaluate_guardian_governance(db)

    assert old_guardian.state == "dormant"
    assert recovering_guardian.state == "active"
    assert db.commits == 1


def test_get_task_center_counts_pending_reviews_correctly():
    user_id = uuid4()
    territory_id = uuid4()
    now = datetime.now(UTC)
    db = _FakeDb(
        execute_results=[
            _ExecuteResult([(territory_id, "area_guide", "Region A")]),
            _ExecuteResult([(uuid4(), now, "POI A", territory_id)]),
            _ExecuteResult([]),
            _ExecuteResult([]),
        ],
        scalar_results=[4, 2],
    )

    result = territory_service.get_task_center(db, user_id)

    assert result.pending_reviews == 1
    assert len(result.items) == 1
    assert result.items[0].task_type == "pending_review"
    assert result.monthly_contributions == 4
    assert result.monthly_helped_count == 2


def test_get_territory_opportunities_requires_existing_territory():
    db = _FakeDb()

    with pytest.raises(HTTPException) as exc:
        territory_service.get_territory_opportunities(db, uuid4())

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Territory not found"


def test_get_territory_opportunities_returns_pending_and_nearby_items():
    territory_id = uuid4()
    now = datetime.now(UTC)
    correction = SimpleNamespace(id=uuid4(), poi_id=uuid4(), created_at=now)
    missing_poi = SimpleNamespace(id=uuid4(), name="POI B", created_at=now, territory_id=territory_id)
    db = _FakeDb(
        get_map={
            (TerritoryRegion, territory_id): SimpleNamespace(id=territory_id, name="Region A"),
            (Poi, correction.poi_id): SimpleNamespace(id=correction.poi_id, name="POI A"),
        },
        scalars_results=[_ScalarResult(all_value=[correction]), _ScalarResult(all_value=[missing_poi])],
        execute_results=[_ExecuteResult([])],
    )

    result = territory_service.get_territory_opportunities(db, territory_id)

    assert result.territory_id == territory_id
    assert len(result.items) == 2
    assert {item.task_type for item in result.items} == {"pending_review", "nearby_opportunity"}
