from types import SimpleNamespace
from uuid import uuid4

from app.services.notification_service import (
    notify_correction_accepted,
    notify_source_itinerary_updated,
)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, results):
        self._results = results
        self._idx = 0

    def execute(self, _stmt):
        rows = self._results[self._idx]
        self._idx += 1
        return _Rows(rows)


def test_notify_source_itinerary_updated_filters_by_status(monkeypatch):
    created = []

    def _stub_create_notification(_db, **kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr("app.services.notification_service.create_notification", _stub_create_notification)

    db = _FakeDb(
        [
            [
                (uuid4(), uuid4(), "draft"),
                (uuid4(), uuid4(), "in_progress"),
                (uuid4(), uuid4(), "published"),
            ]
        ]
    )

    count = notify_source_itinerary_updated(
        db,
        source_itinerary_id=uuid4(),
        source_snapshot_id=uuid4(),
        sender_user_id=uuid4(),
        source_title="Test Plan",
        changed_fields={"visibility"},
        has_removed_items=False,
        has_modified_items=False,
    )

    assert count == 2
    assert len(created) == 2
    assert all(row["severity"] == "critical" for row in created)


def test_notify_correction_accepted_sends_submitter_and_related(monkeypatch):
    created = []

    def _stub_create_notification(_db, **kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr("app.services.notification_service.create_notification", _stub_create_notification)

    submitter_id = uuid4()
    related_user = uuid4()
    related_itinerary = uuid4()
    db = _FakeDb(
        [
            [
                (related_user, related_itinerary),
                (related_user, related_itinerary),
                (submitter_id, uuid4()),
            ]
        ]
    )
    correction = SimpleNamespace(
        id=uuid4(),
        submitter_user_id=submitter_id,
        poi_id=uuid4(),
        source_poi_name_snapshot="POI A",
    )

    count = notify_correction_accepted(
        db,
        correction=correction,
        correction_type_code="temporary_closed",
        reviewer_user_id=uuid4(),
        poi_name_snapshot="POI A",
    )

    assert count == 2
    assert len(created) == 2
    assert created[0]["recipient_user_id"] == submitter_id
    assert created[0]["severity"] == "critical"
    assert created[1]["recipient_user_id"] == related_user
