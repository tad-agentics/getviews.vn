"""Tests for A.1 cross-niche format insight (cross_format.py).

Pure-Python tests with a fake Supabase client so they run without
infra. Cover the gating thresholds (returns None when sample/spread
too thin) + the aggregation correctness (top_hooks ranked by avg_views).
"""

from __future__ import annotations

from typing import Any

import pytest


def _imports():
    try:
        from getviews_pipeline.cross_format import (
            MIN_NICHES_WITH_FORMAT,
            MIN_TOTAL_SAMPLE,
            TOP_HOOKS_LIMIT,
            get_cross_format_signal,
        )
        return get_cross_format_signal, MIN_NICHES_WITH_FORMAT, MIN_TOTAL_SAMPLE, TOP_HOOKS_LIMIT
    except ModuleNotFoundError:
        pytest.skip("pydantic not installed in test env")


# ── Fake Supabase ─────────────────────────────────────────────────────


class _Exec:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Q:
    """Records a fluent query path; resolves data from a path dispatcher."""

    def __init__(self, table: str, dispatcher: dict[str, Any]) -> None:
        self._table = table
        self._dispatcher = dispatcher
        self._format_axis_filter: str | None = None
        self._content_class_filter: int | None = None
        self._cc_in_filter: list[int] | None = None

    def select(self, *_: Any, **__: Any) -> "_Q":
        return self

    def eq(self, col: str, val: Any) -> "_Q":
        if col == "format_axis":
            self._format_axis_filter = val
        elif col == "id":
            self._content_class_filter = int(val)
        return self

    def in_(self, col: str, vals: Any) -> "_Q":
        if col == "content_class_id":
            self._cc_in_filter = list(vals)
        return self

    def gt(self, *_: Any, **__: Any) -> "_Q":
        return self

    def gte(self, *_: Any, **__: Any) -> "_Q":
        return self

    def limit(self, *_: Any, **__: Any) -> "_Q":
        return self

    def maybe_single(self) -> "_Q":
        return self

    def execute(self) -> _Exec:
        if self._table == "content_classifications":
            if self._content_class_filter is not None:
                return _Exec(self._dispatcher.get(("cc_by_id", self._content_class_filter)))
            if self._format_axis_filter is not None:
                return _Exec(self._dispatcher.get(("cc_by_format", self._format_axis_filter), []))
        if self._table == "video_corpus":
            return _Exec(self._dispatcher.get(("corpus", tuple(self._cc_in_filter or [])), []))
        return _Exec(None)


class _Client:
    def __init__(self, dispatcher: dict[str, Any]) -> None:
        self._dispatcher = dispatcher

    def table(self, name: str) -> _Q:
        return _Q(name, self._dispatcher)


# ── Tests ─────────────────────────────────────────────────────────────


def test_returns_none_when_content_class_id_missing() -> None:
    fn, *_ = _imports()
    sb = _Client({})
    assert fn(sb, content_class_id=None) is None
    assert fn(sb, content_class_id=0) is None


def test_returns_none_when_content_class_unmapped() -> None:
    fn, *_ = _imports()
    sb = _Client({("cc_by_id", 999): None})
    assert fn(sb, content_class_id=999) is None


def test_returns_none_when_too_few_niches_have_format() -> None:
    fn, *_ = _imports()
    # 2 niches share the format → below MIN_NICHES_WITH_FORMAT (3).
    dispatcher = {
        ("cc_by_id", 6): {"format_axis": "pov_storytelling"},
        ("cc_by_format", "pov_storytelling"): [{"id": 6}, {"id": 20}],
        ("corpus", (6, 20)): [
            {"video_id": "v1", "niche_id": 1, "hook_type": "pov", "views": 50000},
            {"video_id": "v2", "niche_id": 2, "hook_type": "pov", "views": 60000},
            # All 25 rows from just 2 niches — sample is high but spread is low.
            *[
                {"video_id": f"v{i}", "niche_id": (i % 2) + 1, "hook_type": "pov", "views": 30000 + i * 100}
                for i in range(3, 28)
            ],
        ],
    }
    sb = _Client(dispatcher)
    assert fn(sb, content_class_id=6) is None


def test_returns_none_when_total_sample_too_thin() -> None:
    fn, *_ = _imports()
    # 4 distinct niches but only 10 rows → below MIN_TOTAL_SAMPLE (20).
    dispatcher = {
        ("cc_by_id", 6): {"format_axis": "pov_storytelling"},
        ("cc_by_format", "pov_storytelling"): [{"id": 6}],
        ("corpus", (6,)): [
            {"video_id": f"v{i}", "niche_id": (i % 4) + 1, "hook_type": "pov", "views": 50000}
            for i in range(10)
        ],
    }
    sb = _Client(dispatcher)
    assert fn(sb, content_class_id=6) is None


def test_returns_signal_when_thresholds_met() -> None:
    fn, *_ = _imports()
    # 5 distinct niches × 6 rows each = 30 sample, well above thresholds.
    rows = []
    for niche in range(1, 6):  # niches 1..5
        for r in range(6):
            rows.append({
                "video_id": f"v{niche}-{r}",
                "niche_id": niche,
                "hook_type": "pov" if r < 4 else "story_open",
                "views": 100_000 + niche * 10_000 + r * 100,
            })
    dispatcher = {
        ("cc_by_id", 6): {"format_axis": "pov_storytelling"},
        ("cc_by_format", "pov_storytelling"): [{"id": 6}],
        ("corpus", (6,)): rows,
    }
    sb = _Client(dispatcher)
    out = fn(sb, content_class_id=6)
    assert out is not None
    assert out["format_axis"] == "pov_storytelling"
    assert out["format_label_vi"] == "POV / Storytelling"
    assert out["niches_with_format"] == 5
    assert out["total_sample_size"] == 30
    # Top hooks ranked: pov has 4 rows × 5 niches = wider spread + more rows.
    assert len(out["top_hooks"]) >= 1
    assert out["top_hooks"][0]["hook_type"] in ("pov", "story_open")


def test_top_hooks_skip_single_row_buckets() -> None:
    fn, *_ = _imports()
    # 5 niches × 4 rows of 'pov' + 1 single-row 'one_off' that should be filtered.
    rows = [
        {"video_id": f"p{i}", "niche_id": (i % 5) + 1, "hook_type": "pov", "views": 50000}
        for i in range(20)
    ]
    rows.append({"video_id": "single", "niche_id": 1, "hook_type": "one_off", "views": 999_999})
    dispatcher = {
        ("cc_by_id", 6): {"format_axis": "pov_storytelling"},
        ("cc_by_format", "pov_storytelling"): [{"id": 6}],
        ("corpus", (6,)): rows,
    }
    sb = _Client(dispatcher)
    out = fn(sb, content_class_id=6)
    assert out is not None
    hook_types = {h["hook_type"] for h in out["top_hooks"]}
    assert "one_off" not in hook_types  # filtered: <2 rows
    assert "pov" in hook_types
