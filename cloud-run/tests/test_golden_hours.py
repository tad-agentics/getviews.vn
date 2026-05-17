"""Unit tests for Vietnam ICT golden-hour windows."""

from __future__ import annotations

from datetime import UTC, datetime

from getviews_pipeline.golden_hours import in_vietnam_golden_window


def test_morning_window_ict() -> None:
    # 2026-05-13 Wed 07:30 ICT = 00:30 UTC
    dt = datetime(2026, 5, 13, 0, 30, tzinfo=UTC)
    assert in_vietnam_golden_window(dt) is True


def test_outside_lunch_dead_zone_ict() -> None:
    # Wed 15:00 ICT = 08:00 UTC
    dt = datetime(2026, 5, 13, 8, 0, tzinfo=UTC)
    assert in_vietnam_golden_window(dt) is False


def test_thursday_evening_peak_ict() -> None:
    # 2026-05-14 is Thursday — 20:30 ICT = 13:30 UTC
    dt = datetime(2026, 5, 14, 13, 30, tzinfo=UTC)
    assert in_vietnam_golden_window(dt) is True


def test_late_night_band() -> None:
    # 23:00 ICT = 16:00 UTC
    dt = datetime(2026, 5, 13, 16, 0, tzinfo=UTC)
    assert in_vietnam_golden_window(dt) is True
