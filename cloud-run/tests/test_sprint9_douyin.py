"""Sprint 9 — §8 Douyin origin matcher + signals."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.diagnose_sections import DOUYIN_SECTION_MIN_SALIENCE, select_sections_to_emit
from getviews_pipeline.douyin_match import (
    adoption_stage_from_lag,
    enrich_analysis_with_douyin_match,
    migration_fit_from_adapt_level,
)
from getviews_pipeline.signals.douyin import extract_douyin_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


class _Query:
    def __init__(self, row: dict[str, Any] | None):
        self._row = row

    def select(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def eq(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def order(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def limit(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def execute(self) -> Any:
        data = [self._row] if self._row else []
        return type("R", (), {"data": data})()


class _MockSb:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def table(self, _name: str) -> _Query:
        return _Query(self._row)


class _CapturingSb:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row
        self.eq_calls: list[tuple[str, Any]] = []

    def table(self, _name: str) -> _CapturingQuery:
        return _CapturingQuery(self, self._row)


class _CapturingQuery:
    def __init__(self, parent: _CapturingSb, row: dict[str, Any] | None) -> None:
        self._parent = parent
        self._row = row

    def select(self, *_a: Any, **_k: Any) -> _CapturingQuery:
        return self

    def eq(self, col: str, val: Any) -> _CapturingQuery:
        self._parent.eq_calls.append((col, val))
        return self

    def order(self, *_a: Any, **_k: Any) -> _CapturingQuery:
        return self

    def limit(self, *_a: Any, **_k: Any) -> _CapturingQuery:
        return self

    def execute(self) -> Any:
        data = [self._row] if self._row else []
        return type("R", (), {"data": data})()


def test_adoption_stage_lag() -> None:
    assert adoption_stage_from_lag(3) == "leading_edge"
    assert adoption_stage_from_lag(14) == "mid_curve"
    assert adoption_stage_from_lag(100) == "trailing"
    assert adoption_stage_from_lag(-2) == "leading_edge"


def test_migration_fit_from_adapt() -> None:
    assert migration_fit_from_adapt_level("green") == "clean_adapt"
    assert migration_fit_from_adapt_level("yellow") == "needs_localization"
    assert migration_fit_from_adapt_level("red") == "poor_fit"
    assert migration_fit_from_adapt_level(None) == "unknown"


def test_enrich_analysis_mutates_when_peer_exists(monkeypatch: Any) -> None:
    monkeypatch.setenv("GETVIEWS_DOUYIN_ORIGIN_MATCH", "1")
    row = {
        "video_id": "777",
        "posted_at": "2026-05-01T00:00:00+00:00",
        "adapt_level": "yellow",
        "views": 100000,
    }
    sb = _MockSb(row)
    analysis: dict[str, Any] = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "x",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "niche_classification": {
            "creator_niche_slug": "beauty",
            "format_axis": "review_unboxing",
            "confidence": 0.9,
            "rationale": "test",
            "alternative_creator_niche_slug": None,
        },
    }
    enrich_analysis_with_douyin_match(
        analysis,
        {"posted_at": "2026-05-05T00:00:00+00:00"},
        sb,
    )
    assert analysis["douyin_origin"]["douyin_aweme_id"] == "777"
    assert analysis["vietnam_adoption_stage"] == "leading_edge"
    assert analysis["migration_fit_assessment"] == "needs_localization"


def test_douyin_signals_and_section_gate() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "douyin_origin": {
                "douyin_aweme_id": "999",
                "lag_days": 30,
                "first_seen_douyin": "2026-01-01",
                "first_seen_vietnam": "2026-01-31",
            },
            "vietnam_adoption_stage": "trailing",
            "migration_fit_assessment": "poor_fit",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = extract_douyin_signals(ctx)
    assert len(sigs) == 2
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx, depth="deep")
    assert "douyin_origin" in out
    trailing = next(s for s in sigs if s.id == "douyin_origin_peer")
    assert trailing.salience == DOUYIN_SECTION_MIN_SALIENCE


def test_enrich_skips_when_disabled(monkeypatch: Any) -> None:
    monkeypatch.setenv("GETVIEWS_DOUYIN_ORIGIN_MATCH", "0")
    analysis: dict[str, Any] = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "x",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "niche_classification": {"creator_niche_slug": "beauty"},
    }
    enrich_analysis_with_douyin_match(analysis, {}, _MockSb({"video_id": "1"}))
    assert "douyin_origin" not in analysis


def test_enrich_queries_douyin_with_normalized_hook_type(monkeypatch: Any) -> None:
    """Gemini may emit ``tutorial``; DB stores ``how_to`` — matcher must align."""
    monkeypatch.setenv("GETVIEWS_DOUYIN_ORIGIN_MATCH", "1")
    row = {
        "video_id": "888",
        "posted_at": "2026-05-01T00:00:00+00:00",
        "adapt_level": "green",
        "views": 50_000,
    }
    sb = _CapturingSb(row)
    analysis: dict[str, Any] = {
        "hook_analysis": {
            "hook_type": "tutorial",
            "hook_phrase": "x",
        },
        "niche_classification": {"creator_niche_slug": "beauty"},
    }
    enrich_analysis_with_douyin_match(analysis, {"posted_at": "2026-05-10T00:00:00+00:00"}, sb)
    assert ("hook_type", "how_to") in sb.eq_calls
    assert analysis["douyin_origin"]["douyin_aweme_id"] == "888"
