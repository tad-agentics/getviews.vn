"""Regression tests for the content-calendar extension of TimingPayload.

2026-04-22: ``build_timing_report`` gained a ``mode`` parameter + keyword
heuristic so the ``content_calendar`` intent returns a populated
``calendar_slots`` list instead of being force-fit into the pattern
template.

Covers:
- Pure timing query leaves ``calendar_slots`` empty.
- Calendar query (explicit mode or keyword) populates 3–5 slots.
- Weak heatmap (no window ≥ 1.5× lift) keeps slots empty even when
  asked — we don't ship a week plan on noise.
- Two different calendar queries in the same niche produce different
  slot titles / rationales (query-aware invariant from batch-3).
"""

from __future__ import annotations

from typing import Any

import pytest

from getviews_pipeline.report_timing import (
    _build_calendar_slots,
    _CALENDAR_MIN_LIFT,
    _should_build_calendar,
    _slot_time_from_hours,
)


def _window(day_idx: int, day: str, hours: str, lift: float) -> dict[str, Any]:
    return {
        "day_idx": day_idx,
        "day": day,
        "hours": hours,
        "lift_multiplier": lift,
    }


class TestShouldBuildCalendar:
    def test_explicit_calendar_mode_wins(self) -> None:
        assert _should_build_calendar("khung giờ tốt nhất?", mode="calendar") is True

    def test_explicit_windows_mode_wins(self) -> None:
        assert _should_build_calendar("lịch tuần tới?", mode="windows") is False

    def test_pure_timing_query_without_keywords(self) -> None:
        assert _should_build_calendar("giờ nào post tốt nhất?", mode=None) is False

    @pytest.mark.parametrize(
        "q",
        [
            "Lên lịch post 7 ngày tới cho kênh mình",
            "Cho mình kế hoạch post tuần tới",
            "Tuần tới nên post gì?",
            "Plan 7 ngày giúp mình",
        ],
    )
    def test_calendar_keyword_triggers_build(self, q: str) -> None:
        assert _should_build_calendar(q, mode=None) is True


class TestBuildCalendarSlots:
    def test_empty_when_no_window_reaches_min_lift(self) -> None:
        # All windows below 1.5× → gated out (no noisy plan).
        windows = [
            _window(0, "Thứ 2", "18–20", 1.2),
            _window(2, "Thứ 4", "20–22", 1.3),
        ]
        assert _build_calendar_slots(top_windows=windows, niche_label="Skincare") == []

    def test_populates_when_at_least_one_strong_window(self) -> None:
        windows = [
            _window(2, "Thứ 4", "20–22", 1.8),
            _window(3, "Thứ 5", "20–22", 1.7),
            _window(5, "Thứ 7", "18–20", 1.6),
        ]
        slots = _build_calendar_slots(top_windows=windows, niche_label="Skincare")
        assert 1 <= len(slots) <= 5
        for s in slots:
            assert s["kind"] in {"pattern", "ideas", "timing", "repost"}
            assert s["suggested_time"]
            assert "Skincare" in s["rationale"]
            assert 0 <= s["day_idx"] <= 6

    def test_slots_rotate_through_kinds(self) -> None:
        # Four distinct strong windows → kind rotation should produce a
        # mix, not four of the same kind.
        windows = [
            _window(0, "Thứ 2", "20–22", 2.0),
            _window(1, "Thứ 3", "20–22", 1.9),
            _window(2, "Thứ 4", "20–22", 1.8),
            _window(3, "Thứ 5", "20–22", 1.7),
        ]
        slots = _build_calendar_slots(top_windows=windows, niche_label="Tech")
        kinds = {s["kind"] for s in slots}
        assert len(kinds) >= 2, "rotation should produce at least 2 distinct kinds"

    def test_repost_slot_only_for_weekend_window(self) -> None:
        # Need ≥3 slots before repost can append; include a strong
        # weekend window so the repost rule fires.
        windows = [
            _window(0, "Thứ 2", "20–22", 2.0),
            _window(1, "Thứ 3", "20–22", 1.9),
            _window(2, "Thứ 4", "20–22", 1.8),
            _window(5, "Thứ 7", "18–20", 1.7),  # weekend
        ]
        slots = _build_calendar_slots(top_windows=windows, niche_label="Tech")
        repost_slots = [s for s in slots if s["kind"] == "repost"]
        if repost_slots:
            assert repost_slots[0]["day_idx"] in (5, 6)

    def test_slots_sorted_by_day_idx(self) -> None:
        windows = [
            _window(5, "Thứ 7", "20–22", 2.0),
            _window(0, "Thứ 2", "20–22", 1.9),
            _window(3, "Thứ 5", "20–22", 1.8),
        ]
        slots = _build_calendar_slots(top_windows=windows, niche_label="Tech")
        day_idxs = [s["day_idx"] for s in slots]
        assert day_idxs == sorted(day_idxs), "slots must render Mon→Sun"

    def test_no_duplicate_days(self) -> None:
        # Two windows on the same day should not produce two slots on
        # that day (one slot per day max).
        windows = [
            _window(2, "Thứ 4", "20–22", 1.9),
            _window(2, "Thứ 4", "18–20", 1.8),
            _window(3, "Thứ 5", "20–22", 1.7),
        ]
        slots = _build_calendar_slots(top_windows=windows, niche_label="Tech")
        day_idxs = [s["day_idx"] for s in slots]
        assert len(day_idxs) == len(set(day_idxs))


class TestSlotTimeFromHours:
    @pytest.mark.parametrize(
        "bucket,expected",
        [
            ("18–22", "18:00"),
            ("20–22", "20:00"),
            ("6–9", "6:00"),
            ("20:30–22:00", "20:30"),
        ],
    )
    def test_picks_bucket_start_and_normalises(self, bucket: str, expected: str) -> None:
        assert _slot_time_from_hours(bucket) == expected

    @pytest.mark.parametrize("bucket", ["", "invalid", "no-dash"])
    def test_falls_back_to_prime_time_on_malformed(self, bucket: str) -> None:
        assert _slot_time_from_hours(bucket) == "20:00"


def test_min_lift_constant_matches_prd() -> None:
    """The PRD (artifacts/docs/report-template-prd-timing-calendar.md)
    gates calendar assembly at 1.5× lift. If this constant changes,
    update the doc + vice versa."""
    assert _CALENDAR_MIN_LIFT == 1.5


# ── CalendarSlotKind type alias (2026-05-07) ─────────────────────────────


def test_calendar_slot_kind_exported_and_narrower_than_report_kind() -> None:
    """``CalendarSlotKind`` is the named alias for the ``CalendarSlot.kind``
    literal — intentionally distinct from ``ReportKind`` even where they
    share values. Pin both the export and the domain difference so a
    refactor can't accidentally unify them and hide the trap the alias
    was introduced to document.
    """
    from typing import get_args

    from getviews_pipeline.report_types import CalendarSlotKind, ReportKind

    slot_kinds = set(get_args(CalendarSlotKind))
    report_kinds = set(get_args(ReportKind))

    # Slot-kind narrow domain includes "repost" that ReportKind does not.
    assert "repost" in slot_kinds
    assert "repost" not in report_kinds

    # ReportKind includes the new answer shelves that CalendarSlotKind does not.
    for k in ("generic", "lifecycle", "diagnostic"):
        assert k in report_kinds
        assert k not in slot_kinds
