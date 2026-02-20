from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.itinerary_diff_action import ItineraryDiffAction
from app.services import itinerary_service
from app.services.itinerary_service import (
    get_itinerary_diff_action_statuses,
    submit_itinerary_diff_actions_batch,
)


class _ScalarsResult:
    def __init__(self, first_value=None, all_values=None):
        self._first_value = first_value
        self._all_values = all_values or []

    def first(self):
        return self._first_value

    def all(self):
        return self._all_values


def test_submit_diff_actions_batch_requires_ignore_reason(monkeypatch):
    owner_id = uuid4()
    itinerary_id = uuid4()
    snapshot_id = uuid4()
    fork_rel = SimpleNamespace(
        source_itinerary_id=uuid4(),
        forked_itinerary_id=itinerary_id,
        forked_by_user_id=owner_id,
        source_snapshot_id=snapshot_id,
    )

    class _Db:
        def __init__(self):
            self.added = []

        def get(self, model, entity_id):
            name = getattr(model, "__name__", "")
            if name == "Itinerary":
                return SimpleNamespace(id=itinerary_id, creator_user_id=owner_id)
            if name == "ItinerarySnapshot":
                return SimpleNamespace(id=snapshot_id)
            return None

        def scalars(self, _stmt):
            return _ScalarsResult(first_value=fork_rel)

        def add(self, value):
            self.added.append(value)

        def commit(self):
            return None

    monkeypatch.setattr(
        itinerary_service,
        "_latest_source_snapshot_id",
        lambda *_args, **_kwargs: snapshot_id,
    )
    monkeypatch.setattr(
        itinerary_service,
        "_build_action_status_map",
        lambda *_args, **_kwargs: {},
    )

    payload = SimpleNamespace(
        source_snapshot_id=snapshot_id,
        actions=[
            SimpleNamespace(
                diff_key="meta:title",
                diff_type="metadata",
                action="ignored",
                reason=None,
            ),
        ],
    )
    db = _Db()

    with pytest.raises(HTTPException) as exc_info:
        submit_itinerary_diff_actions_batch(db, itinerary_id, SimpleNamespace(id=owner_id), payload)

    assert exc_info.value.status_code == 400
    assert "requires reason" in str(exc_info.value.detail)
    assert len(db.added) == 0


def test_submit_diff_actions_batch_returns_warning_and_counts(monkeypatch):
    owner_id = uuid4()
    itinerary_id = uuid4()
    snapshot_id = uuid4()
    latest_snapshot_id = uuid4()
    fork_rel = SimpleNamespace(
        source_itinerary_id=uuid4(),
        forked_itinerary_id=itinerary_id,
        forked_by_user_id=owner_id,
        source_snapshot_id=snapshot_id,
    )

    class _Db:
        def __init__(self):
            self.added = []
            self.committed = False

        def get(self, model, entity_id):
            name = getattr(model, "__name__", "")
            if name == "Itinerary":
                return SimpleNamespace(id=itinerary_id, creator_user_id=owner_id)
            if name == "ItinerarySnapshot":
                return SimpleNamespace(id=snapshot_id)
            return None

        def scalars(self, _stmt):
            return _ScalarsResult(first_value=fork_rel)

        def add(self, value):
            self.added.append(value)

        def commit(self):
            self.committed = True

    monkeypatch.setattr(
        itinerary_service,
        "_latest_source_snapshot_id",
        lambda *_args, **_kwargs: latest_snapshot_id,
    )
    monkeypatch.setattr(
        itinerary_service,
        "_build_action_status_map",
        lambda *_args, **_kwargs: {"meta:title": "applied"},
    )

    payload = SimpleNamespace(
        source_snapshot_id=snapshot_id,
        actions=[
            SimpleNamespace(
                diff_key="meta:title",
                diff_type="metadata",
                action="applied",
                reason=None,
            ),
            SimpleNamespace(
                diff_key="added:d2-s1",
                diff_type="added",
                action="ignored",
                reason="保留当前方案",
            ),
        ],
    )
    db = _Db()

    result = submit_itinerary_diff_actions_batch(
        db,
        itinerary_id,
        SimpleNamespace(id=owner_id),
        payload,
    )

    assert result.applied_count == 1
    assert result.ignored_count == 1
    assert result.rolled_back_count == 0
    assert len(result.warnings) == 1
    assert db.committed is True
    assert any(isinstance(item, ItineraryDiffAction) for item in db.added)


def test_get_itinerary_diff_action_statuses_returns_latest_rows():
    owner_id = uuid4()
    itinerary_id = uuid4()
    snapshot_id = uuid4()
    fork_rel = SimpleNamespace(
        source_itinerary_id=uuid4(),
        forked_itinerary_id=itinerary_id,
        forked_by_user_id=owner_id,
        source_snapshot_id=snapshot_id,
    )
    older = SimpleNamespace(
        diff_key="meta:title",
        diff_type="metadata",
        action="read",
        reason=None,
        actor_user_id=owner_id,
        created_at=datetime(2026, 2, 19, tzinfo=UTC),
    )
    newer = SimpleNamespace(
        diff_key="meta:title",
        diff_type="metadata",
        action="applied",
        reason=None,
        actor_user_id=owner_id,
        created_at=datetime(2026, 2, 19, 1, tzinfo=UTC),
    )
    another = SimpleNamespace(
        diff_key="added:d2-s1",
        diff_type="added",
        action="ignored",
        reason="已有备选",
        actor_user_id=owner_id,
        created_at=datetime(2026, 2, 19, 2, tzinfo=UTC),
    )

    class _Db:
        def __init__(self):
            self._scalars_call = 0

        def get(self, model, entity_id):
            name = getattr(model, "__name__", "")
            if name == "Itinerary":
                return SimpleNamespace(id=itinerary_id, creator_user_id=owner_id)
            return None

        def scalars(self, _stmt):
            self._scalars_call += 1
            if self._scalars_call == 1:
                return _ScalarsResult(first_value=fork_rel)
            return _ScalarsResult(all_values=[another, newer, older])

    db = _Db()
    result = get_itinerary_diff_action_statuses(
        db,
        itinerary_id,
        SimpleNamespace(id=owner_id),
        snapshot_id,
    )

    assert result.source_snapshot_id == snapshot_id
    assert len(result.items) == 2
    by_key = {item.diff_key: item for item in result.items}
    assert by_key["meta:title"].action == "applied"
    assert by_key["added:d2-s1"].reason == "已有备选"
