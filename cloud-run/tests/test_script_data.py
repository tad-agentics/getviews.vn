"""B.4.2 — script_data helpers (no Supabase)."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.script_data import (
    _fmt_delta_pct,
    _pattern_label,
    fetch_hook_patterns_for_niche,
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


def _build_sb_for_hook_patterns(
    *,
    niche_label: str = "Skincare",
    ni_sample_size: int = 100,
    he_rows: list[dict] | None = None,
    corpus_rows: list[dict] | None = None,
) -> MagicMock:
    """Stitch a Supabase mock that feeds ``fetch_hook_patterns_for_niche``."""
    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "niche_taxonomy":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
                MagicMock(data={"name_vn": niche_label, "name_en": niche_label})
            )
        elif name == "niche_intelligence":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
                MagicMock(
                    data={
                        "organic_avg_views": 10_000,
                        "commerce_avg_views": 0,
                        "sample_size": ni_sample_size,
                    }
                )
            )
        elif name == "hook_effectiveness":
            m.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=he_rows or [])
            )
        elif name == "video_corpus":
            m.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=corpus_rows or [])
            )
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


def test_fetch_hook_patterns_uses_hook_effectiveness_when_populated() -> None:
    sb = _build_sb_for_hook_patterns(
        he_rows=[
            {
                "hook_type": "how_to",
                "avg_views": 20_000,
                "sample_size": 8,
                "trend_direction": "up",
                "computed_at": "2026-04-20T00:00:00Z",
            }
        ],
        corpus_rows=[],
    )
    out = fetch_hook_patterns_for_niche(sb, 2)
    assert len(out["hook_patterns"]) == 1
    assert out["hook_patterns"][0]["pattern"] == "Hướng dẫn nhanh"
    assert out["hook_patterns"][0]["uses"] == 8


def test_fetch_hook_patterns_falls_back_to_video_corpus_when_he_empty() -> None:
    """BUG-13 regression: when hook_effectiveness has no rows for a niche
    but video_corpus does, the script page must still render a hook
    leaderboard instead of "Chưa có dữ liệu hook cho ngách.""" ""
    sb = _build_sb_for_hook_patterns(
        he_rows=[],
        corpus_rows=[
            {"hook_type": "how_to", "views": 50_000},
            {"hook_type": "how_to", "views": 10_000},
            {"hook_type": "how_to", "views": 30_000},
            {"hook_type": "question", "views": 80_000},
            {"hook_type": "question", "views": 40_000},
            # ``none`` + empty should be skipped by the aggregator.
            {"hook_type": "none", "views": 99_999},
            {"hook_type": "", "views": 12_345},
        ],
    )
    out = fetch_hook_patterns_for_niche(sb, 2)
    patterns = out["hook_patterns"]
    assert len(patterns) == 2
    # Highest avg_views first: question avg = 60K, how_to avg = 30K.
    assert patterns[0]["pattern"] == "Câu hỏi mở đầu"
    assert patterns[0]["uses"] == 2
    assert patterns[0]["avg_views"] == 60_000
    assert patterns[1]["pattern"] == "Hướng dẫn nhanh"
    assert patterns[1]["uses"] == 3
    # Citation sample_size reflects the largest bucket count.
    assert out["citation"]["sample_size"] == 3


def test_fetch_hook_patterns_returns_empty_when_both_sources_empty() -> None:
    sb = _build_sb_for_hook_patterns(he_rows=[], corpus_rows=[])
    out = fetch_hook_patterns_for_niche(sb, 2)
    assert out["hook_patterns"] == []
