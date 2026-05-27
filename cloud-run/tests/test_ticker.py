"""Unit tests for ticker — the Home marquee's five-bucket aggregator.

Each bucket is tested in isolation against a fake Supabase client; only the
round-robin interleave + failure-mode behaviour exercise `compute_ticker`
end-to-end.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from getviews_pipeline.ticker import (
    _breakout_items,
    _caution_items,
    _new_hook_items,
    _rising_kol_items,
    _sound_items,
    compute_ticker,
)

# ── Fake Supabase ──────────────────────────────────────────────────────────


class _Exec:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _NotModifier:
    """Mimics supabase-py's `.not_.is_(col, 'null')` fluent call."""

    def __init__(self, parent: _Query) -> None:
        self._parent = parent

    def is_(self, *_: Any) -> _Query:
        return self._parent


class _Query:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, Any]] = []

    def select(self, *_: Any, **__: Any) -> _Query:    return self
    def eq(self, col: str, val: Any) -> _Query:
        self._filters.append((col, val))
        return self
    def in_(self, *_: Any, **__: Any) -> _Query:       return self
    def gte(self, *_: Any, **__: Any) -> _Query:       return self
    def order(self, *_: Any, **__: Any) -> _Query:     return self
    def limit(self, n: int) -> _Query:
        self._limit = n
        return self

    @property
    def not_(self) -> _NotModifier:
        return _NotModifier(self)

    def execute(self) -> _Exec:
        rows = list(self._rows)
        for col, val in self._filters:
            if not any(col in r for r in self._rows):
                continue
            rows = [r for r in rows if r.get(col) == val]
        limit = getattr(self, "_limit", len(rows))
        return _Exec(rows[:limit])


class _Client:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self._tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self._tables.get(name, []))


NOW = datetime.now(UTC)
SINCE = (NOW - timedelta(days=7)).isoformat()
NICHE = 3


# ── breakout ──────────────────────────────────────────────────────────────


def test_breakout_drops_below_threshold() -> None:
    client = _Client({
        "video_corpus": [
            {"video_id": "v1", "creator_handle": "a", "views": 5_000_000,
             "breakout_multiplier": 3.4},
            {"video_id": "v2", "creator_handle": "b", "views": 50_000,
             "breakout_multiplier": 1.5},  # under 2.0 — dropped
        ],
    })
    items = _breakout_items(client, NICHE, SINCE)
    assert len(items) == 1
    assert items[0].target_id == "v1"
    assert items[0].bucket == "breakout"
    assert "3.4×" in items[0].headline_vi
    assert "5M" in items[0].headline_vi


def test_breakout_prefers_reference_eligible() -> None:
    client = _Client({
        "video_corpus": [
            {"video_id": "ineligible", "creator_handle": "b", "views": 9_000_000,
             "breakout_multiplier": 5.0, "reference_eligible": False},
            {"video_id": "eligible1", "creator_handle": "a", "views": 5_000_000,
             "breakout_multiplier": 3.4, "reference_eligible": True},
            {"video_id": "eligible2", "creator_handle": "c", "views": 4_000_000,
             "breakout_multiplier": 2.8, "reference_eligible": True},
        ],
    })
    items = _breakout_items(client, NICHE, SINCE)
    assert len(items) == 2
    assert {i.target_id for i in items} == {"eligible1", "eligible2"}


def test_breakout_handles_missing_multiplier() -> None:
    client = _Client({
        "video_corpus": [
            {"video_id": "v1", "creator_handle": "a", "views": 1000,
             "breakout_multiplier": None},
        ],
    })
    assert _breakout_items(client, NICHE, SINCE) == []


# ── hook_mới ──────────────────────────────────────────────────────────────


def test_new_hook_filters_to_niche_spread() -> None:
    client = _Client({
        "video_patterns": [
            {"id": "p1", "display_name": "POV keeps going", "niche_spread": [NICHE, 9],
             "weekly_instance_count": 30, "is_active": True, "first_seen_at": SINCE},
            {"id": "p2", "display_name": "Off-niche", "niche_spread": [99],
             "weekly_instance_count": 100, "is_active": True, "first_seen_at": SINCE},
        ],
    })
    items = _new_hook_items(client, NICHE, SINCE)
    assert [i.target_id for i in items] == ["p1"]
    assert items[0].bucket == "hook_mới"
    assert "POV keeps going" in items[0].headline_vi


def test_new_hook_skips_zero_week_count_uses_live_corpus() -> None:
    """weekly_instance_count may be 0 while corpus rows exist (BUG-11 cron lag)."""
    client = _Client({
        "video_patterns": [
            {"id": "p1", "display_name": "Nhịp cắt cận cảnh nhanh", "niche_spread": [NICHE],
             "weekly_instance_count": 0, "is_active": True, "first_seen_at": SINCE},
            {"id": "p2", "display_name": "Stale zero", "niche_spread": [NICHE],
             "weekly_instance_count": 0, "is_active": True, "first_seen_at": SINCE},
        ],
        "video_corpus": [
            {"pattern_id": "p1", "indexed_at": SINCE},
            {"pattern_id": "p1", "indexed_at": SINCE},
            {"pattern_id": "p1", "indexed_at": SINCE},
        ],
    })
    items = _new_hook_items(client, NICHE, SINCE)
    assert len(items) == 1
    assert items[0].target_id == "p1"
    assert "3 video tuần này" in items[0].headline_vi
    assert "0 video" not in items[0].headline_vi


def test_new_hook_caps_at_two() -> None:
    client = _Client({
        "video_patterns": [
            {"id": f"p{i}", "display_name": f"P{i}", "niche_spread": [NICHE],
             "weekly_instance_count": 100 - i, "is_active": True, "first_seen_at": SINCE}
            for i in range(5)
        ],
    })
    items = _new_hook_items(client, NICHE, SINCE)
    assert len(items) == 2
    assert [i.target_id for i in items] == ["p0", "p1"]


# ── cảnh_báo ──────────────────────────────────────────────────────────────


def test_caution_requires_prev_above_spread_floor() -> None:
    # A pattern going from 5 → 1 dropped 80% but has < 10 prev (below
    # pattern_spread floor), so it's noise, not signal. Skipped.
    client = _Client({
        "video_patterns": [
            {"id": "noise", "display_name": "x", "niche_spread": [NICHE],
             "weekly_instance_count": 1, "weekly_instance_count_prev": 5, "is_active": True},
            {"id": "cool",  "display_name": "Cooling", "niche_spread": [NICHE],
             "weekly_instance_count": 3, "weekly_instance_count_prev": 20, "is_active": True},
        ],
    })
    items = _caution_items(client, NICHE, SINCE)
    assert [i.target_id for i in items] == ["cool"]
    assert "85%" in items[0].headline_vi


def test_caution_threshold_is_40_percent_drop() -> None:
    # 12 → 8 is a 33% drop — not flagged. 20 → 10 is 50% — flagged.
    client = _Client({
        "video_patterns": [
            {"id": "mild",  "display_name": "Mild", "niche_spread": [NICHE],
             "weekly_instance_count": 8,  "weekly_instance_count_prev": 12, "is_active": True},
            {"id": "steep", "display_name": "Steep", "niche_spread": [NICHE],
             "weekly_instance_count": 10, "weekly_instance_count_prev": 20, "is_active": True},
        ],
    })
    items = _caution_items(client, NICHE, SINCE)
    assert [i.target_id for i in items] == ["steep"]


# ── kol_nổi ───────────────────────────────────────────────────────────────


def test_rising_kol_ranks_by_max_bm() -> None:
    client = _Client({
        "video_corpus": [
            {"creator_handle": "a", "views": 100_000, "creator_followers": 10_000, "breakout_multiplier": 4.0},
            {"creator_handle": "a", "views": 50_000,  "creator_followers": 10_000, "breakout_multiplier": 1.8},
            {"creator_handle": "b", "views": 200_000, "creator_followers": 50_000, "breakout_multiplier": 2.5},
            {"creator_handle": "c", "views": 800_000, "creator_followers": 1_000_000, "breakout_multiplier": 1.1},
        ],
    })
    items = _rising_kol_items(client, NICHE, SINCE)
    assert [i.target_id for i in items] == ["a", "b"]
    assert "@a" in items[0].headline_vi


def test_rising_kol_drops_handles_below_breakout_floor() -> None:
    client = _Client({
        "video_corpus": [
            {"creator_handle": "a", "views": 100_000, "creator_followers": 0, "breakout_multiplier": 1.5},
        ],
    })
    assert _rising_kol_items(client, NICHE, SINCE) == []


# ── âm_thanh ─────────────────────────────────────────────────────────────


def test_sounds_only_take_latest_week() -> None:
    # Two weeks of data — only the latest week's entries should appear.
    # ``_sound_items`` resolves the legacy niche → content_class_ids via
    # ``creator_niche_content_classes`` before reading the (now
    # class-scoped) ``trending_sounds`` table.
    client = _Client({
        "creator_niche_content_classes": [
            {"content_class_id": 101},
        ],
        "trending_sounds": [
            {"sound_id": "s1", "sound_name": "Fresh 1", "usage_count": 30,
             "total_views": 2_500_000, "week_of": "2026-04-13"},
            {"sound_id": "s2", "sound_name": "Fresh 2", "usage_count": 25,
             "total_views": 1_200_000, "week_of": "2026-04-13"},
            {"sound_id": "old", "sound_name": "Stale",  "usage_count": 50,
             "total_views": 9_000_000, "week_of": "2026-04-06"},
        ],
    })
    items = _sound_items(client, NICHE, SINCE)
    assert [i.target_id for i in items] == ["s1", "s2"]
    assert items[0].bucket == "âm_thanh"


# ── interleave + fail-open ────────────────────────────────────────────────


def test_compute_ticker_interleaves_round_robin() -> None:
    client = _Client({
        "video_corpus": [
            {"video_id": "v1", "creator_handle": "a", "views": 5_000_000, "breakout_multiplier": 4.0},
            {"video_id": "v2", "creator_handle": "b", "views": 3_000_000, "breakout_multiplier": 3.0},
        ],
        "video_patterns": [
            {"id": "p1", "display_name": "P1", "niche_spread": [NICHE],
             "weekly_instance_count": 50, "is_active": True, "first_seen_at": SINCE},
            {"id": "p2", "display_name": "P2", "niche_spread": [NICHE],
             "weekly_instance_count": 40, "is_active": True, "first_seen_at": SINCE},
        ],
    })
    items = asyncio.run(compute_ticker(client, NICHE))
    buckets = [i.bucket for i in items]
    # First two items must come from different buckets (round-robin).
    assert buckets[0] != buckets[1]


def test_compute_ticker_fails_open_per_bucket() -> None:
    class _Boom:
        def table(self, name: str) -> _Query:
            if name == "video_corpus":
                raise RuntimeError("boom")
            return _Query([])  # every other bucket returns empty cleanly

    items = asyncio.run(compute_ticker(_Boom(), NICHE))
    assert items == []  # degrades to empty, not an error
