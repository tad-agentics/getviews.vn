"""D4a (2026-06-04) — Kho Douyin · feed read-model tests.

Mocks Supabase so tests don't hit the network. Each case targets one
slice of ``fetch_douyin_feed``:
  • Niche fetch + active-only filter.
  • Corpus fetch scoped to active-niche IDs.
  • Row serialization (JSONB translator_notes, hashtags_zh, type
    coercions, NULL-safe defaults).
  • Defensive paths (niche fetch error → empty feed; corpus fetch
    error → niches still surface).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.douyin_data import _serialize_video, fetch_douyin_feed

# ── Mock helpers ────────────────────────────────────────────────────


def _niche_chain(rows: list[dict[str, Any]] | Exception) -> MagicMock:
    """Mock for the douyin_niche_taxonomy SELECT chain."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    if isinstance(rows, Exception):
        chain.execute.side_effect = rows
    else:
        chain.execute.return_value = MagicMock(data=rows)
    return chain


def _video_chain(rows: list[dict[str, Any]] | Exception) -> MagicMock:
    """Mock for the douyin_video_corpus SELECT chain."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    if isinstance(rows, Exception):
        chain.execute.side_effect = rows
    else:
        chain.execute.return_value = MagicMock(data=rows)
    return chain


def _client_for(niche_chain: MagicMock, video_chain: MagicMock) -> MagicMock:
    """Single client whose ``table()`` routes by table name."""
    def _route(name: str) -> MagicMock:
        if name == "douyin_niche_taxonomy":
            return niche_chain
        if name == "douyin_video_corpus":
            return video_chain
        return MagicMock()

    client = MagicMock()
    client.table.side_effect = _route
    return client


# ── _serialize_video ─────────────────────────────────────────────────


def test_serialize_video_coerces_types_and_safe_defaults() -> None:
    row = {
        "video_id": "v1",
        "douyin_url": "https://www.douyin.com/video/v1",
        "niche_id": "1",  # comes back as string sometimes
        "creator_handle": "alice",
        "creator_name": "Alice",
        "thumbnail_url": "https://cdn/thumb.jpg",
        "video_url": "https://cdn/v.mp4",
        "video_duration": "32.5",
        "views": "1000000",
        "likes": "50000",
        "saves": "120000",
        "engagement_rate": "5.5",
        "title_zh": "睡前3件事",
        "title_vi": "Trước khi ngủ làm 3 việc",
        "sub_vi": "3 việc trước khi ngủ — 1 tháng sau khác",
        "hashtags_zh": ["#养生", "#健康"],
        "adapt_level": "green",
        "adapt_reason": "Wellness universal.",
        "eta_weeks_min": "2",
        "eta_weeks_max": "4",
        "cn_rise_pct": "240.5",
        "translator_notes": [
            {"tag": "TỪ NGỮ", "note": "睡前 = trước khi ngủ"},
            {"tag": "NHẠC NỀN", "note": "Đổi remix Jay Chou → piano slow"},
        ],
        "synth_computed_at": "2026-06-04T00:00:00+00:00",
        "indexed_at": "2026-06-03T22:00:00+00:00",
    }
    out = _serialize_video(row)
    assert out["niche_id"] == 1
    assert out["video_duration"] == 32.5
    assert out["views"] == 1_000_000
    assert out["likes"] == 50_000
    assert out["saves"] == 120_000
    assert out["engagement_rate"] == 5.5
    assert out["eta_weeks_min"] == 2
    assert out["eta_weeks_max"] == 4
    assert out["cn_rise_pct"] == 240.5
    assert out["adapt_level"] == "green"
    assert len(out["translator_notes"]) == 2
    assert out["hashtags_zh"] == ["#养生", "#健康"]


def test_serialize_video_handles_null_synth_fields() -> None:
    """Freshly-ingested rows haven't been graded yet — adapt_* is NULL.
    The serializer must surface NULL (not error) so the FE can render
    the 'human review pending' caveat."""
    row = {
        "video_id": "v1",
        "niche_id": 1,
        "views": 100,
        "likes": 10,
        "saves": 0,
        # All synth fields missing.
    }
    out = _serialize_video(row)
    assert out["adapt_level"] is None
    assert out["adapt_reason"] is None
    assert out["eta_weeks_min"] is None
    assert out["eta_weeks_max"] is None
    assert out["cn_rise_pct"] is None
    assert out["translator_notes"] == []


def test_serialize_video_drops_malformed_translator_notes() -> None:
    """JSONB row with garbage entries — keep only valid {tag, note} pairs."""
    row = {
        "video_id": "v1",
        "niche_id": 1,
        "views": 100,
        "likes": 0,
        "saves": 0,
        "translator_notes": [
            {"tag": "TỪ NGỮ", "note": "valid"},
            {"tag": "NHẠC NỀN"},        # missing note
            {"note": "missing tag"},
            "not a dict",
            None,
            {"tag": "BỐI CẢNH", "note": "another valid"},
        ],
    }
    out = _serialize_video(row)
    assert len(out["translator_notes"]) == 2
    assert {n["tag"] for n in out["translator_notes"]} == {"TỪ NGỮ", "BỐI CẢNH"}


def test_serialize_video_drops_whitespace_only_translator_notes() -> None:
    """D6e (audit L4) — a whitespace-only ``note`` field passes basic
    truthiness but renders an empty card on the FE modal. Strip
    before checking truthiness so we never emit blank notes."""
    row = {
        "video_id": "v1",
        "niche_id": 1,
        "views": 100, "likes": 0, "saves": 0,
        "translator_notes": [
            {"tag": "TỪ NGỮ", "note": "valid note"},
            {"tag": "BỐI CẢNH", "note": "   "},       # whitespace only — drop
            {"tag": "NHẠC NỀN", "note": "\t\n"},      # tab/newline — drop
            {"tag": "  ", "note": "blank tag"},        # whitespace tag — drop
            {"tag": "ĐẠO CỤ", "note": "another valid"},
        ],
    }
    out = _serialize_video(row)
    assert len(out["translator_notes"]) == 2
    assert {n["tag"] for n in out["translator_notes"]} == {"TỪ NGỮ", "ĐẠO CỤ"}


def test_serialize_video_strips_whitespace_around_translator_notes() -> None:
    """Surrounding whitespace on tag / note should be trimmed in the
    serializer output even when the trimmed value is non-empty."""
    row = {
        "video_id": "v1",
        "niche_id": 1,
        "views": 100, "likes": 0, "saves": 0,
        "translator_notes": [
            {"tag": "  TỪ NGỮ  ", "note": "  surrounded by spaces  "},
        ],
    }
    out = _serialize_video(row)
    assert out["translator_notes"][0]["tag"] == "TỪ NGỮ"
    assert out["translator_notes"][0]["note"] == "surrounded by spaces"


def test_serialize_video_drops_blank_hashtags() -> None:
    """TEXT[] from PostgREST may contain empty strings — strip them."""
    row = {
        "video_id": "v1",
        "niche_id": 1,
        "views": 100,
        "likes": 0,
        "saves": 0,
        "hashtags_zh": ["#养生", "", "  ", "#健康"],
    }
    out = _serialize_video(row)
    assert out["hashtags_zh"] == ["#养生", "#健康"]


def test_serialize_video_handles_garbage_numeric_fields() -> None:
    """A bad ingest could leave non-numeric strings in numeric columns —
    the serializer must coerce to None instead of raising."""
    row = {
        "video_id": "v1",
        "niche_id": "not-an-int",
        "views": "garbage",
        "likes": None,
        "saves": None,
        "engagement_rate": "x",
        "video_duration": "y",
    }
    out = _serialize_video(row)
    assert out["niche_id"] is None
    assert out["views"] == 0           # _int_or_none → None → fallback 0
    assert out["engagement_rate"] is None
    assert out["video_duration"] is None


# ── fetch_douyin_feed ────────────────────────────────────────────────


def test_feed_returns_active_niches_and_their_videos() -> None:
    niches = [
        {"id": 1, "slug": "wellness", "name_vn": "Wellness",
         "name_zh": "养生", "name_en": "Wellness"},
        {"id": 2, "slug": "tech", "name_vn": "Tech",
         "name_zh": "科技", "name_en": "Tech"},
    ]
    videos = [
        {"video_id": "v1", "niche_id": 1, "title_zh": "X",
         "views": 1_000_000, "likes": 0, "saves": 0},
        {"video_id": "v2", "niche_id": 2, "title_zh": "Y",
         "views": 500_000, "likes": 0, "saves": 0},
    ]
    client = _client_for(_niche_chain(niches), _video_chain(videos))
    out = fetch_douyin_feed(client)
    assert len(out["niches"]) == 2
    assert len(out["videos"]) == 2
    # Niche slugs threaded through.
    assert {n["slug"] for n in out["niches"]} == {"wellness", "tech"}


def test_feed_filters_videos_to_active_niches_only() -> None:
    """Niche taxonomy SELECT must use ``.eq('active', True)`` — paused
    niches' videos must NEVER surface."""
    niches = [
        {"id": 1, "slug": "wellness", "name_vn": "W", "name_zh": "Z", "name_en": "W"},
    ]
    niche_chain = _niche_chain(niches)
    video_chain = _video_chain([])
    client = _client_for(niche_chain, video_chain)
    fetch_douyin_feed(client)
    niche_chain.eq.assert_called_with("active", True)
    # Video query must be scoped to active niche IDs.
    video_chain.in_.assert_called_with("niche_id", [1])


def test_feed_returns_empty_videos_when_no_active_niches() -> None:
    """Don't waste a video round-trip when the niche taxonomy is empty."""
    client = MagicMock()
    niche_chain = _niche_chain([])
    video_chain = MagicMock()  # should never be called

    def _route(name: str) -> MagicMock:
        if name == "douyin_niche_taxonomy":
            return niche_chain
        return video_chain

    client.table.side_effect = _route
    out = fetch_douyin_feed(client)
    assert out["niches"] == []
    assert out["videos"] == []
    video_chain.select.assert_not_called()


def test_feed_returns_empty_when_niche_query_errors() -> None:
    """Defensive: niche fetch failing returns an empty feed instead of
    a 500 — the FE renders an empty-state."""
    client = _client_for(
        _niche_chain(RuntimeError("PostgREST 500")),
        _video_chain([]),
    )
    out = fetch_douyin_feed(client)
    assert out == {"niches": [], "videos": []}


def test_feed_keeps_niches_when_video_query_errors() -> None:
    """If niches load but videos fail, surface niches anyway — chip
    strip still renders, grid renders empty-state."""
    niches = [
        {"id": 1, "slug": "wellness", "name_vn": "W",
         "name_zh": "Z", "name_en": "W"},
    ]
    client = _client_for(
        _niche_chain(niches),
        _video_chain(RuntimeError("PostgREST 500")),
    )
    out = fetch_douyin_feed(client)
    assert len(out["niches"]) == 1
    assert out["videos"] == []


def test_feed_orders_videos_by_views_desc_server_side() -> None:
    """Default ordering is views DESC so the first paint is meaningful
    even before the FE applies its sort dropdown."""
    niches = [{"id": 1, "slug": "wellness", "name_vn": "W",
               "name_zh": "Z", "name_en": "W"}]
    video_chain = _video_chain([])
    client = _client_for(_niche_chain(niches), video_chain)
    fetch_douyin_feed(client)
    video_chain.order.assert_called_with("views", desc=True)


def test_feed_drops_video_rows_with_empty_video_id() -> None:
    """video_id is the natural key — a row without one shouldn't
    surface."""
    niches = [{"id": 1, "slug": "w", "name_vn": "W",
               "name_zh": "Z", "name_en": "W"}]
    videos = [
        {"video_id": "v1", "niche_id": 1, "views": 100, "likes": 0, "saves": 0},
        {"video_id": "", "niche_id": 1, "views": 50, "likes": 0, "saves": 0},
        {"video_id": None, "niche_id": 1, "views": 25, "likes": 0, "saves": 0},
    ]
    client = _client_for(_niche_chain(niches), _video_chain(videos))
    out = fetch_douyin_feed(client)
    assert len(out["videos"]) == 1
    assert out["videos"][0]["video_id"] == "v1"
