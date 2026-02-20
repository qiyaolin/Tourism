from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from PIL import Image

from app.models.poi import Poi
from app.models.poi_correction import PoiCorrection
from app.models.poi_correction_type import PoiCorrectionType
from app.services.poi_correction_service import review_correction, strip_exif_bytes


def test_strip_exif_bytes_removes_exif_marker():
    image = Image.new("RGB", (10, 10), color=(255, 0, 0))
    source = BytesIO()
    exif = Image.Exif()
    exif[0x010E] = "Test EXIF"
    image.save(source, format="JPEG", exif=exif)
    raw = source.getvalue()
    assert b"Exif" in raw

    cleaned = strip_exif_bytes(raw, "jpg")

    assert cleaned
    assert b"Exif" not in cleaned


class _FakeDb:
    def __init__(self, correction, correction_type, poi):
        self._correction = correction
        self._correction_type = correction_type
        self._poi = poi
        self.committed = False
        self.added = []

    def get(self, model, entity_id):
        if model is PoiCorrection and entity_id == self._correction.id:
            return self._correction
        if model is PoiCorrectionType and entity_id == self._correction_type.id:
            return self._correction_type
        if model is Poi and entity_id == self._poi.id:
            return self._poi
        return None

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True

    def refresh(self, _value):
        return None

    def scalar(self, _stmt):
        return 0

    def scalars(self, _stmt):
        return SimpleNamespace(all=lambda: [])


def test_review_correction_accept_updates_ticket_price():
    correction = SimpleNamespace(
        id=uuid4(),
        poi_id=uuid4(),
        type_id=uuid4(),
        status="pending",
        reviewer_user_id=None,
        proposed_value="66.5",
        review_comment=None,
        reviewed_at=None,
        submitter_user_id=uuid4(),
        details="价格已调整",
        photo_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        before_snapshot=None,
        after_snapshot=None,
        source_poi_name_snapshot="测试景点",
        source_itinerary_id=None,
        source_itinerary_title_snapshot=None,
        source_itinerary_author_snapshot=None,
    )
    correction_type = SimpleNamespace(
        id=correction.type_id,
        code="ticket_price_changed",
        label="票价信息有误",
        target_field="ticket_price",
        value_kind="number",
        placeholder=None,
        sort_order=10,
    )
    poi = SimpleNamespace(id=correction.poi_id, ticket_price=50.0, opening_hours=None, address=None)
    current_user = SimpleNamespace(id=uuid4())
    db = _FakeDb(correction, correction_type, poi)

    result = review_correction(db, correction.id, "accepted", "已核实", current_user)

    assert db.committed is True
    assert result.poi_updated is True
    assert poi.ticket_price == 66.5
    assert result.correction.status == "accepted"


def test_review_correction_opening_hours_rejects_invalid_format():
    correction = SimpleNamespace(
        id=uuid4(),
        poi_id=uuid4(),
        type_id=uuid4(),
        status="pending",
        reviewer_user_id=None,
        proposed_value="9:00-18:00",
        review_comment=None,
        reviewed_at=None,
        submitter_user_id=uuid4(),
        details=None,
        photo_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        before_snapshot=None,
        after_snapshot=None,
        source_poi_name_snapshot="测试景点",
        source_itinerary_id=None,
        source_itinerary_title_snapshot=None,
        source_itinerary_author_snapshot=None,
    )
    correction_type = SimpleNamespace(
        id=correction.type_id,
        code="opening_hours_changed",
        label="营业时间变更",
        target_field="opening_hours",
        value_kind="string",
        placeholder=None,
        sort_order=20,
    )
    poi = SimpleNamespace(id=correction.poi_id, ticket_price=50.0, opening_hours="09:00-18:00", address=None)
    current_user = SimpleNamespace(id=uuid4())
    db = _FakeDb(correction, correction_type, poi)

    with pytest.raises(HTTPException):
        review_correction(db, correction.id, "accepted", "已核实", current_user)


def test_review_correction_opening_hours_accepts_time_range():
    correction = SimpleNamespace(
        id=uuid4(),
        poi_id=uuid4(),
        type_id=uuid4(),
        status="pending",
        reviewer_user_id=None,
        proposed_value="10:00-18:30",
        review_comment=None,
        reviewed_at=None,
        submitter_user_id=uuid4(),
        details=None,
        photo_url=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        before_snapshot=None,
        after_snapshot=None,
        source_poi_name_snapshot="测试景点",
        source_itinerary_id=None,
        source_itinerary_title_snapshot=None,
        source_itinerary_author_snapshot=None,
    )
    correction_type = SimpleNamespace(
        id=correction.type_id,
        code="opening_hours_changed",
        label="营业时间变更",
        target_field="opening_hours",
        value_kind="string",
        placeholder=None,
        sort_order=20,
    )
    poi = SimpleNamespace(id=correction.poi_id, ticket_price=50.0, opening_hours="09:00-18:00", address=None)
    current_user = SimpleNamespace(id=uuid4())
    db = _FakeDb(correction, correction_type, poi)

    result = review_correction(db, correction.id, "accepted", "已核实", current_user)

    assert result.poi_updated is True
    assert poi.opening_hours == "10:00-18:30"
