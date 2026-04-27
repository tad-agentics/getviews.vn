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


# ── /script/idea-references — IdeaRefStrip data source ─────────────────

from getviews_pipeline.script_data import (
    _resolve_hook_type,
    _score_idea_reference,
    fetch_idea_references_for_niche,
)


def test_resolve_hook_type_accepts_raw_enum() -> None:
    assert _resolve_hook_type("question") == "question"
    assert _resolve_hook_type("  bold_claim ") == "bold_claim"


def test_resolve_hook_type_accepts_vn_label() -> None:
    assert _resolve_hook_type("Câu hỏi mở đầu") == "question"
    assert _resolve_hook_type("Số liệu gây sốc") == "shock_stat"


def test_resolve_hook_type_unknown_returns_none() -> None:
    assert _resolve_hook_type(None) is None
    assert _resolve_hook_type("") is None
    assert _resolve_hook_type("garbage_label_no_match") is None


def test_score_idea_reference_zero_views_clamps_to_50_floor() -> None:
    assert _score_idea_reference(0, hook_match=False) == 50
    # Hook match adds 30 even at 0 views.
    assert _score_idea_reference(0, hook_match=True) == 80


def test_score_idea_reference_views_log_bonus_caps_at_20() -> None:
    # Massive views + hook match = max 100 (clamped).
    assert _score_idea_reference(10_000_000, hook_match=True) == 100
    # Same views without hook match = 50 + 20 (log cap) = 70.
    assert _score_idea_reference(10_000_000, hook_match=False) == 70


def _build_sb_for_idea_refs(
    *,
    primary_rows: list[dict] | None = None,
    fallback_rows: list[dict] | None = None,
) -> MagicMock:
    """Stitch a Supabase mock for ``fetch_idea_references_for_niche``.

    The fetcher does TWO ``video_corpus`` queries (primary with hook
    filter + fallback without), so the mock returns a different
    ``data`` payload on each ``.execute()`` call."""
    sb = MagicMock()
    payloads = [
        MagicMock(data=primary_rows or []),
        MagicMock(data=fallback_rows or []),
    ]
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = payloads
    sb.table.return_value = chain
    return sb


def test_fetch_idea_references_primary_pool_only() -> None:
    """When the niche+hook pool returns >= ``limit`` rows, the fetcher
    never falls back to overall niche top-views."""
    primary = [
        {"video_id": f"v{i}", "creator_handle": f"@c{i}",
         "tiktok_url": f"https://tt/v{i}", "thumbnail_url": None,
         "views": 100_000 - i * 10_000, "video_duration": 32.0,
         "hook_type": "question", "hook_phrase": f"Hook #{i}", "caption": ""}
        for i in range(5)
    ]
    sb = _build_sb_for_idea_refs(primary_rows=primary)
    out = fetch_idea_references_for_niche(sb, 7, "question", limit=5)
    assert out["niche_id"] == 7
    assert out["hook_type"] == "question"
    assert len(out["references"]) == 5
    # Hook match → all 5 should score in the upper band (60+ from base+hook).
    assert all(r["match_pct"] >= 80 for r in out["references"])
    # Highest-views row first.
    assert out["references"][0]["video_id"] == "v0"


def test_fetch_idea_references_falls_back_when_primary_thin() -> None:
    """Niche has only 2 videos with the chosen hook_type. Fetcher fills
    the strip from overall niche top-views, marking the fallback rows
    with hook_match=False (lower match%)."""
    primary = [
        {"video_id": "p1", "creator_handle": "@a",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 500_000, "video_duration": 30.0,
         "hook_type": "question", "hook_phrase": "Hook A", "caption": ""},
        {"video_id": "p2", "creator_handle": "@b",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 200_000, "video_duration": 25.0,
         "hook_type": "question", "hook_phrase": "Hook B", "caption": ""},
    ]
    fallback = [
        {"video_id": "p1", "creator_handle": "@a",  # de-duped (already in primary)
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 500_000, "video_duration": 30.0,
         "hook_type": "question", "hook_phrase": "Hook A", "caption": ""},
        {"video_id": "f1", "creator_handle": "@c",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 1_000_000, "video_duration": 28.0,
         "hook_type": "bold_claim", "hook_phrase": "Hook C", "caption": ""},
        {"video_id": "f2", "creator_handle": "@d",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 50_000, "video_duration": 22.0,
         "hook_type": "story_open", "hook_phrase": "", "caption": "Caption snippet"},
    ]
    sb = _build_sb_for_idea_refs(primary_rows=primary, fallback_rows=fallback)
    out = fetch_idea_references_for_niche(sb, 7, "question", limit=5)
    refs = out["references"]
    # 2 primary + 2 fallback (after de-dupe) = 4 rows total.
    assert len(refs) == 4
    ids = [r["video_id"] for r in refs]
    assert "p1" in ids and "p2" in ids and "f1" in ids and "f2" in ids
    # p1 should rank above f1 even though f1 has more views — hook_match
    # contributes 30 points which beats the views log bonus.
    p1 = next(r for r in refs if r["video_id"] == "p1")
    f1 = next(r for r in refs if r["video_id"] == "f1")
    assert p1["match_pct"] > f1["match_pct"]
    # f2 fell back on caption when hook_phrase was empty.
    f2 = next(r for r in refs if r["video_id"] == "f2")
    assert f2["shot_label"] == "Caption snippet"


def test_fetch_idea_references_no_hook_type_uses_only_fallback() -> None:
    """When caller passes hook_type=None, fetcher skips the primary
    query entirely and pulls from overall niche top-views. Mock-side
    we still need to feed the row payload through the FIRST execute()
    call because that's the only one the fetcher makes."""
    fallback = [
        {"video_id": "v1", "creator_handle": "@a",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 100_000, "video_duration": 30.0,
         "hook_type": "question", "hook_phrase": "X", "caption": ""},
    ]
    sb = _build_sb_for_idea_refs(primary_rows=fallback)
    out = fetch_idea_references_for_niche(sb, 7, None, limit=5)
    assert out["hook_type"] is None
    assert len(out["references"]) == 1
    # No hook match (resolved_hook is None), so no 30-point bonus.
    assert out["references"][0]["match_pct"] < 80


def test_fetch_idea_references_excludes_video_ids() -> None:
    primary = [
        {"video_id": "keep", "creator_handle": "@a",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 100_000, "video_duration": 30.0,
         "hook_type": "question", "hook_phrase": "X", "caption": ""},
        {"video_id": "skip", "creator_handle": "@b",
         "tiktok_url": "url", "thumbnail_url": None,
         "views": 200_000, "video_duration": 25.0,
         "hook_type": "question", "hook_phrase": "Y", "caption": ""},
    ]
    sb = _build_sb_for_idea_refs(primary_rows=primary)
    out = fetch_idea_references_for_niche(
        sb, 7, "question", limit=5, exclude_video_ids=["skip"],
    )
    ids = [r["video_id"] for r in out["references"]]
    assert ids == ["keep"]
