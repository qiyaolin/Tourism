from types import SimpleNamespace
from uuid import uuid4

from app.models.itinerary import Itinerary
from app.models.itinerary_snapshot import ItinerarySnapshot
from app.models.user import User
from app.services.itinerary_service import fork_public_itinerary, get_itinerary_diff


class _ScalarsResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _FakeDb:
    def __init__(self, source_itinerary, source_author, snapshot, fork_rel, owned_itinerary):
        self.source_itinerary = source_itinerary
        self.source_author = source_author
        self.snapshot = snapshot
        self.fork_rel = fork_rel
        self.owned_itinerary = owned_itinerary
        self.added = []
        self.committed = False

    def get(self, model, entity_id):
        if model is Itinerary and entity_id == self.source_itinerary.id:
            return self.source_itinerary
        if model is Itinerary and entity_id == self.owned_itinerary.id:
            return self.owned_itinerary
        if model is User and entity_id == self.source_author.id:
            return self.source_author
        if model is ItinerarySnapshot and entity_id == self.snapshot.id:
            return self.snapshot
        return None

    def add(self, value):
        if isinstance(value, Itinerary) and value.id is None:
            value.id = uuid4()
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, _value):
        return None

    def scalars(self, _stmt):
        return _ScalarsResult(self.snapshot if self.fork_rel is None else self.fork_rel)


def test_fork_public_itinerary_copies_snapshot_items(monkeypatch):
    source_id = uuid4()
    source_itinerary = SimpleNamespace(
        id=source_id,
        title="北京三日游",
        destination="北京",
        days=3,
        creator_user_id=uuid4(),
        status="in_progress",
        visibility="private",
    )
    source_author = SimpleNamespace(id=source_itinerary.creator_user_id, nickname="原作者")
    snapshot = SimpleNamespace(
        id=uuid4(),
        snapshot_json={
            "meta": {"destination": "北京", "days": 3, "cover_image_url": None},
            "items": [
                {
                    "day_index": 1,
                    "sort_order": 1,
                    "poi_id": str(uuid4()),
                    "start_time": "09:00:00",
                    "duration_minutes": 90,
                    "cost": 35.0,
                    "tips": "先去热门点位",
                }
            ],
        },
    )
    current_user = SimpleNamespace(id=uuid4())
    db = _FakeDb(
        source_itinerary,
        source_author,
        snapshot,
        None,
        SimpleNamespace(id=uuid4(), creator_user_id=current_user.id),
    )

    result = fork_public_itinerary(db, source_id, current_user)

    assert result.source_itinerary_id == source_id
    assert result.source_author_nickname == "原作者"
    assert result.title.startswith("来自@原作者：")
    new_itinerary = next(value for value in db.added if isinstance(value, Itinerary))
    assert new_itinerary.status == "in_progress"
    assert new_itinerary.visibility == "private"
    assert db.committed is True


def test_get_itinerary_diff_returns_field_level_result(monkeypatch):
    owner_id = uuid4()
    source_itinerary_id = uuid4()
    forked_itinerary_id = uuid4()
    snapshot = SimpleNamespace(
        id=uuid4(),
        snapshot_json={
            "meta": {
                "title": "原始标题",
                "destination": "北京",
                "days": 2,
                "status": "published",
                "visibility": "public",
                "cover_image_url": None,
            },
            "items": [
                {
                    "day_index": 1,
                    "sort_order": 1,
                    "poi_id": str(uuid4()),
                    "poi_name": "故宫",
                    "poi_type": "sightseeing",
                    "longitude": 116.397,
                    "latitude": 39.916,
                    "address": "东城区",
                    "opening_hours": "08:30-17:00",
                    "ticket_price": 60.0,
                    "start_time": "09:00:00",
                    "duration_minutes": 120,
                    "cost": 60.0,
                    "tips": "提前预约",
                }
            ],
        },
    )
    fork_rel = SimpleNamespace(
        source_itinerary_id=source_itinerary_id,
        forked_itinerary_id=forked_itinerary_id,
        forked_by_user_id=owner_id,
        source_snapshot_id=snapshot.id,
    )
    owned_itinerary = SimpleNamespace(id=forked_itinerary_id, creator_user_id=owner_id)
    db = _FakeDb(
        source_itinerary=SimpleNamespace(id=source_itinerary_id, creator_user_id=uuid4()),
        source_author=SimpleNamespace(id=uuid4(), nickname="x"),
        snapshot=snapshot,
        fork_rel=fork_rel,
        owned_itinerary=owned_itinerary,
    )

    monkeypatch.setattr(
        "app.services.itinerary_service._build_snapshot_payload",
        lambda _db, _itinerary: {
            "meta": {
                "title": "新的标题",
                "destination": "北京",
                "days": 2,
                "status": "in_progress",
                "visibility": "private",
                "cover_image_url": None,
            },
            "items": [
                {
                    "day_index": 1,
                    "sort_order": 1,
                    "poi_id": snapshot.snapshot_json["items"][0]["poi_id"],
                    "poi_name": "故宫",
                    "poi_type": "sightseeing",
                    "longitude": 116.397,
                    "latitude": 39.916,
                    "address": "东城区",
                    "opening_hours": "08:30-17:00",
                    "ticket_price": 60.0,
                    "start_time": "10:00:00",
                    "duration_minutes": 120,
                    "cost": 80.0,
                    "tips": "改成中午",
                },
                {
                    "day_index": 2,
                    "sort_order": 1,
                    "poi_id": str(uuid4()),
                    "poi_name": "景山公园",
                    "poi_type": "sightseeing",
                    "longitude": 116.397,
                    "latitude": 39.925,
                    "address": "西城区",
                    "opening_hours": "06:00-21:00",
                    "ticket_price": 2.0,
                    "start_time": "15:00:00",
                    "duration_minutes": 60,
                    "cost": 2.0,
                    "tips": None,
                },
            ],
        },
    )

    result = get_itinerary_diff(db, forked_itinerary_id, SimpleNamespace(id=owner_id))

    assert result.summary.added == 1
    assert result.summary.removed == 0
    assert result.summary.modified == 1
    assert any(item.field == "title" for item in result.metadata_diffs)
    assert any(item.field == "status" for item in result.metadata_diffs)
    assert any(diff.key == "d2-s1" for diff in result.added_items)
