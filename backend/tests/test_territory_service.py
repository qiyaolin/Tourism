from types import SimpleNamespace
from uuid import uuid4

from app.services import territory_service
from app.services.territory_service import (
    _cell_for_point,
    _polygon_for_cell,
    can_review_correction_in_territory,
)


def test_cell_for_point_uses_floor_grid():
    cell = _cell_for_point(116.405, 39.915, 0.1)
    assert cell == (1164, 399)


def test_polygon_for_cell_closed_ring():
    polygon = _polygon_for_cell(1, 2, 0.5)
    assert polygon.startswith("POLYGON((")
    assert polygon.endswith("))")
    assert polygon.count(",") == 4


def test_can_review_correction_admin_always_true():
    user = SimpleNamespace(id=uuid4(), role="admin")
    assert can_review_correction_in_territory(SimpleNamespace(), user, uuid4()) is True


def test_can_review_correction_guardian_by_membership(monkeypatch):
    territory_id = uuid4()
    user = SimpleNamespace(id=uuid4(), role="user")
    monkeypatch.setattr(
        territory_service,
        "active_guardian_territory_ids",
        lambda _db, _user_id: [territory_id],
    )
    assert can_review_correction_in_territory(SimpleNamespace(), user, territory_id) is True
    assert can_review_correction_in_territory(SimpleNamespace(), user, uuid4()) is False
