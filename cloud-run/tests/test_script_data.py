"""B.4.2 — script_data helpers (no Supabase)."""

from __future__ import annotations

from getviews_pipeline.script_data import (
    _fmt_delta_pct,
    _pattern_label,
    latest_hook_effectiveness_rows,
)


def test_fmt_delta_pct() -> None:
    assert _fmt_delta_pct(2000, 1000) == "+100%"
    assert _fmt_delta_pct(500, 1000) == "-50%"
    assert _fmt_delta_pct(0, 0) == "+0%"


def test_pattern_label_known() -> None:
    assert _pattern_label("question") == "Câu hỏi mở đầu"


def test_latest_hook_effectiveness_rows_dedupes_newest() -> None:
    rows = [
        {
            "hook_type": "pov",
            "avg_views": 100,
            "sample_size": 5,
            "computed_at": "2026-01-01T00:00:00Z",
        },
        {
            "hook_type": "pov",
            "avg_views": 999,
            "sample_size": 9,
            "computed_at": "2026-02-01T00:00:00Z",
        },
        {
            "hook_type": "story_open",
            "avg_views": 50,
            "sample_size": 3,
            "computed_at": "2026-01-15T00:00:00Z",
        },
    ]
    latest = latest_hook_effectiveness_rows(rows)
    by = {r["hook_type"]: r for r in latest}
    assert by["pov"]["avg_views"] == 999
    assert "story_open" in by
