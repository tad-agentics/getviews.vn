"""Phase C.0.3 — adaptive window selection from corpus counts."""

from __future__ import annotations

import pytest

from getviews_pipeline.adaptive_window import choose_adaptive_window_days


def test_niche_zero_returns_7() -> None:
    assert choose_adaptive_window_days(0, "pattern") == 7


def test_prefers_smallest_window_meeting_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 50, 14: 80, 30: 200}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    assert choose_adaptive_window_days(3, "pattern") == 7


def test_widens_when_7_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 10, 14: 35, 30: 100}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    assert choose_adaptive_window_days(3, "pattern") == 14


def test_ideas_needs_higher_count(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 40, 14: 70, 30: 120}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    assert choose_adaptive_window_days(3, "ideas") == 14


def test_returns_30_when_never_meets_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        lambda _n, _d: 5,
    )
    assert choose_adaptive_window_days(3, "pattern") == 30


# ── Lifecycle + diagnostic report kinds (2026-05-07) ────────────────────────


def test_lifecycle_uses_timing_floor_80(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifecycle needs the same data density as timing — at 50 videos in
    the 7d window it must widen to 14d (where the count clears 80), not
    stay at 7d like pattern would."""
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 50, 14: 90, 30: 200}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    # Pattern (floor 30) stays at 7d with 50 videos …
    assert choose_adaptive_window_days(3, "pattern") == 7
    # … but lifecycle (floor 80) has to widen.
    assert choose_adaptive_window_days(3, "lifecycle") == 14


def test_lifecycle_widens_further_when_14d_still_thin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 40, 14: 60, 30: 120}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    # Lifecycle needs 80 — only 30d clears it.
    assert choose_adaptive_window_days(3, "lifecycle") == 30


def test_diagnostic_uses_pattern_floor_30(monkeypatch: pytest.MonkeyPatch) -> None:
    """Diagnostic benchmarks are aggregate (retention / top sound /
    CTA types) — forgiving, same floor as pattern."""
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 40, 14: 70, 30: 150}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    # 40 videos in 7d ≥ diagnostic floor (30) → return 7.
    assert choose_adaptive_window_days(3, "diagnostic") == 7


def test_diagnostic_widens_when_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 10, 14: 35, 30: 100}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    # 10 videos in 7d < 30 floor; widens to 14d (35 ≥ 30).
    assert choose_adaptive_window_days(3, "diagnostic") == 14


def test_unknown_report_kind_falls_back_to_pattern_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defence in depth — a typo or future value must not silently widen
    to 30 because the floor lookup missed. Falls back to pattern floor
    (30) so the behaviour stays predictable."""
    def fake(niche_id: int, days: int) -> int:
        _ = niche_id
        return {7: 40, 14: 100, 30: 200}.get(days, 0)

    monkeypatch.setattr(
        "getviews_pipeline.adaptive_window.count_video_corpus_for_niche",
        fake,
    )
    assert choose_adaptive_window_days(3, "mystery_kind") == 7  # type: ignore[arg-type]


def test_floor_constants_public() -> None:
    """Keep the floor constants importable so lifecycle compute +
    diagnostic builder can cross-reference without drifting numbers."""
    from getviews_pipeline.adaptive_window import (
        DIAGNOSTIC_SAMPLE_FLOOR,
        IDEAS_SAMPLE_FLOOR,
        LIFECYCLE_SAMPLE_FLOOR,
        PATTERN_SAMPLE_FLOOR,
        TIMING_SAMPLE_FLOOR,
    )
    assert PATTERN_SAMPLE_FLOOR == 30
    assert IDEAS_SAMPLE_FLOOR == 60
    assert TIMING_SAMPLE_FLOOR == 80
    assert LIFECYCLE_SAMPLE_FLOOR == 80
    assert DIAGNOSTIC_SAMPLE_FLOOR == 30
