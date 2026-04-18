"""Unit tests for pulse — the niche's week in four numbers.

Tests run against a fake Supabase client that answers only the two tables
pulse queries (video_corpus, video_patterns). No network, no pytest-asyncio
needed — the aggregate sync path is exercised directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.pulse import VIRAL_BREAKOUT_THRESHOLD, _compute_pulse_sync


# ── Fake Supabase client ───────────────────────────────────────────────────


class _FakeExec:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def select(self, *_: Any, **__: Any) -> "_FakeQuery": return self
    def eq(self, *_: Any, **__: Any) -> "_FakeQuery":     return self
    def gte(self, *_: Any, **__: Any) -> "_FakeQuery":    return self
    def order(self, *_: Any, **__: Any) -> "_FakeQuery":  return self
    def limit(self, *_: Any, **__: Any) -> "_FakeQuery":  return self
    def execute(self) -> _FakeExec:                        return _FakeExec(self._rows)


class _FakeClient:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self._tables = tables

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._tables.get(name, []))


def _iso(dt: datetime) -> str:
    return dt.isoformat()


NICHE = 7
NOW = datetime.now(timezone.utc)
THIS_WEEK = NOW - timedelta(days=3)
LAST_WEEK = NOW - timedelta(days=10)


# ── flags_for_count integration via adequacy field ─────────────────────────


def test_empty_corpus_yields_zero_pulse() -> None:
    client = _FakeClient({"video_corpus": [], "video_patterns": []})
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.views_this_week == 0
    assert stats.videos_this_week == 0
    assert stats.views_delta_pct == 0.0
    assert stats.adequacy == "none"
    assert stats.top_hook_name is None


def test_week_over_week_delta_when_last_week_zero() -> None:
    # When last_week has zero views, delta_pct must not divide by zero —
    # design shows "-" in the UI for that case, backend returns 0.0.
    client = _FakeClient({
        "video_corpus": [
            {"creator_handle": "a", "views": 1000, "breakout_multiplier": None,
             "created_at": _iso(THIS_WEEK)},
        ],
        "video_patterns": [],
    })
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.views_this_week == 1000
    assert stats.views_last_week == 0
    assert stats.views_delta_pct == 0.0


def test_week_over_week_delta_computed() -> None:
    client = _FakeClient({
        "video_corpus": [
            {"creator_handle": "a", "views": 1200, "breakout_multiplier": None,
             "created_at": _iso(THIS_WEEK)},
            {"creator_handle": "b", "views": 1000, "breakout_multiplier": None,
             "created_at": _iso(LAST_WEEK)},
        ],
        "video_patterns": [],
    })
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.views_this_week == 1200
    assert stats.views_last_week == 1000
    assert stats.views_delta_pct == 20.0


def test_viral_count_uses_threshold() -> None:
    # VIRAL_BREAKOUT_THRESHOLD is inclusive on the high side. A video at
    # exactly the threshold counts; just below doesn't.
    client = _FakeClient({
        "video_corpus": [
            {"creator_handle": "a", "views": 500,
             "breakout_multiplier": VIRAL_BREAKOUT_THRESHOLD,
             "created_at": _iso(THIS_WEEK)},
            {"creator_handle": "b", "views": 500,
             "breakout_multiplier": VIRAL_BREAKOUT_THRESHOLD - 0.01,
             "created_at": _iso(THIS_WEEK)},
            {"creator_handle": "c", "views": 500, "breakout_multiplier": None,
             "created_at": _iso(THIS_WEEK)},
        ],
        "video_patterns": [],
    })
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.videos_this_week == 3
    assert stats.viral_count_this_week == 1


def test_new_creators_count_excludes_last_week_handles() -> None:
    # @b appears in both weeks → not new. @a is new. @c appeared only last
    # week → doesn't count for this-week's tally at all.
    client = _FakeClient({
        "video_corpus": [
            {"creator_handle": "a", "views": 100, "breakout_multiplier": None,
             "created_at": _iso(THIS_WEEK)},
            {"creator_handle": "b", "views": 100, "breakout_multiplier": None,
             "created_at": _iso(THIS_WEEK)},
            {"creator_handle": "b", "views": 100, "breakout_multiplier": None,
             "created_at": _iso(LAST_WEEK)},
            {"creator_handle": "c", "views": 100, "breakout_multiplier": None,
             "created_at": _iso(LAST_WEEK)},
        ],
        "video_patterns": [],
    })
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.new_creators_this_week == 1  # only @a


def test_top_hook_is_highest_weekly_count_in_niche() -> None:
    # Two patterns spread into this niche; the one with more weekly instances
    # wins. A third pattern outside this niche is ignored.
    client = _FakeClient({
        "video_corpus": [],
        "video_patterns": [
            {"display_name": "POV: small", "niche_spread": [NICHE, 99],
             "last_seen_at": _iso(THIS_WEEK), "weekly_instance_count": 4, "is_active": True},
            {"display_name": "POV: big",   "niche_spread": [NICHE],
             "last_seen_at": _iso(THIS_WEEK), "weekly_instance_count": 42, "is_active": True},
            {"display_name": "Off niche",  "niche_spread": [99],
             "last_seen_at": _iso(THIS_WEEK), "weekly_instance_count": 100, "is_active": True},
        ],
    })
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.top_hook_name == "POV: big"
    assert stats.new_hooks_this_week == 2  # only the two that spread into NICHE


def test_adequacy_reflects_claim_tier() -> None:
    rows = [
        {"creator_handle": f"u{i}", "views": 100, "breakout_multiplier": None,
         "created_at": _iso(THIS_WEEK)}
        for i in range(35)
    ]
    client = _FakeClient({"video_corpus": rows, "video_patterns": []})
    stats = _compute_pulse_sync(client, NICHE)
    assert stats.videos_this_week == 35
    # 35 ≥ niche_norms (30) but < hook_effectiveness (50)
    assert stats.adequacy == "niche_norms"
