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
