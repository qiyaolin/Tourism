from datetime import UTC, datetime, timedelta

from app.services import bounty_service


def test_haversine_distance_meters_returns_zero_for_same_point():
    distance = bounty_service._haversine_distance_meters(104.071, 30.67, 104.071, 30.67)
    assert round(distance, 2) == 0.0


def test_haversine_distance_meters_for_known_delta():
    distance = bounty_service._haversine_distance_meters(104.071, 30.67, 104.072, 30.67)
    assert 80 <= distance <= 110


def test_evaluate_risk_marks_manual_review_for_missing_exif(monkeypatch):
    monkeypatch.setattr(bounty_service.settings, "bounty_high_freq_daily_limit", 5)
    risk, reasons = bounty_service._evaluate_risk(
        submit_longitude=104.071,
        submit_latitude=30.67,
        exif_captured_at=None,
        exif_longitude=None,
        exif_latitude=None,
        today_count=0,
    )
    assert risk == "manual_review"
    assert "missing_exif_time" in reasons
    assert "missing_exif_location" in reasons


def test_evaluate_risk_marks_manual_review_for_high_frequency(monkeypatch):
    monkeypatch.setattr(bounty_service.settings, "bounty_high_freq_daily_limit", 5)
    now = datetime.now(UTC)
    risk, reasons = bounty_service._evaluate_risk(
        submit_longitude=104.071,
        submit_latitude=30.67,
        exif_captured_at=now,
        exif_longitude=104.071,
        exif_latitude=30.67,
        today_count=5,
    )
    assert risk == "manual_review"
    assert "high_frequency" in reasons


def test_evaluate_risk_returns_normal_when_all_checks_pass(monkeypatch):
    monkeypatch.setattr(bounty_service.settings, "bounty_high_freq_daily_limit", 5)
    monkeypatch.setattr(bounty_service.settings, "bounty_gps_radius_meters", 500)
    now = datetime.now(UTC) - timedelta(hours=2)
    risk, reasons = bounty_service._evaluate_risk(
        submit_longitude=104.071,
        submit_latitude=30.67,
        exif_captured_at=now,
        exif_longitude=104.0711,
        exif_latitude=30.6701,
        today_count=2,
    )
    assert risk == "normal"
    assert reasons == []
