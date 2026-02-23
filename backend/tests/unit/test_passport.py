from app.models.passport import BadgeDef
from app.services.passport_service import calculate_level


def test_calculate_level():
    assert calculate_level(0) == 1
    assert calculate_level(50) == 1
    assert calculate_level(100) == 2
    assert calculate_level(299) == 2
    assert calculate_level(300) == 3
    assert calculate_level(599) == 3
    assert calculate_level(600) == 4
    assert calculate_level(999) == 4
    assert calculate_level(1000) == 5
    assert calculate_level(5000) == 5

def test_badge_def_schema():
    b = BadgeDef(code="test", name="Test Badge", description="Testing", condition_type="test", condition_threshold=1)
    assert b.code == "test"
    assert b.name == "Test Badge"
