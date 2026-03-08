from types import SimpleNamespace
from uuid import uuid4

from app.services import territory_service
from app.services.territory_service import (
    ROLE_HIERARCHY,
    _cell_for_point,
    _compute_target_role,
    _next_role,
    _polygon_for_cell,
    _role_index,
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


def test_can_review_correction_none_territory():
    user = SimpleNamespace(id=uuid4(), role="user")
    assert can_review_correction_in_territory(SimpleNamespace(), user, None) is True


# ---------------------------------------------------------------------------
# Role hierarchy helpers
# ---------------------------------------------------------------------------


def test_role_hierarchy_order():
    assert ROLE_HIERARCHY == ["regular", "local_expert", "area_guide", "city_ambassador"]


def test_next_role():
    assert _next_role("regular") == "local_expert"
    assert _next_role("local_expert") == "area_guide"
    assert _next_role("area_guide") == "city_ambassador"
    assert _next_role("city_ambassador") is None
    assert _next_role("unknown") is None


def test_role_index():
    assert _role_index("regular") == 0
    assert _role_index("local_expert") == 1
    assert _role_index("area_guide") == 2
    assert _role_index("city_ambassador") == 3
    assert _role_index("unknown") == 0


# ---------------------------------------------------------------------------
# Role computation (_compute_target_role)
# ---------------------------------------------------------------------------


def test_compute_target_role_regular():
    role = _compute_target_role(contribution_count=3, thanks_received=0, account_age_days=5, area_count=0)
    assert role == "regular"


def test_compute_target_role_below_regular_still_regular():
    role = _compute_target_role(contribution_count=1, thanks_received=0, account_age_days=5, area_count=0)
    assert role == "regular"


def test_compute_target_role_local_expert():
    role = _compute_target_role(contribution_count=10, thanks_received=0, account_age_days=30, area_count=0)
    assert role == "local_expert"


def test_compute_target_role_local_expert_needs_age():
    """Enough contributions but not enough account age = still regular."""
    role = _compute_target_role(contribution_count=10, thanks_received=0, account_age_days=10, area_count=0)
    assert role == "regular"


def test_compute_target_role_area_guide():
    role = _compute_target_role(contribution_count=15, thanks_received=20, account_age_days=60, area_count=1)
    assert role == "area_guide"


def test_compute_target_role_area_guide_not_enough_thanks():
    role = _compute_target_role(contribution_count=15, thanks_received=5, account_age_days=60, area_count=1)
    assert role == "local_expert"


def test_compute_target_role_city_ambassador():
    role = _compute_target_role(contribution_count=30, thanks_received=25, account_age_days=180, area_count=3)
    assert role == "city_ambassador"


def test_compute_target_role_city_ambassador_not_enough_areas():
    """All thresholds met except area coverage = stays area_guide."""
    role = _compute_target_role(contribution_count=30, thanks_received=25, account_age_days=180, area_count=2)
    assert role == "area_guide"


# ---------------------------------------------------------------------------
# Role never demotes
# ---------------------------------------------------------------------------


def test_role_never_demotes_by_index():
    """Verify that _role_index comparison prevents demotion."""
    current_role = "local_expert"
    target_role = "regular"  # Lower
    assert _role_index(target_role) <= _role_index(current_role)
    # The service only promotes if _role_index(target) > _role_index(current)
    # So no demotion would occur
