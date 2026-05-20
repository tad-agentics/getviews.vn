"""Embedded reference tiles must resolve from the synthesis pool with content proximity."""

from __future__ import annotations

from getviews_pipeline.gemini import (
    EMBED_CONTRACT_VERSION,
    count_valid_embedded_tiles,
    repair_diagnosis_vi_embedded_tiles,
    _sanitize_diagnosis_embedded_tiles,
    _validate_diagnosis_vi_citations,
)


def _slim(aid: str, desc: str, *, proximity: int, source: str = "corpus") -> dict:
    return {
        "aweme_id": aid,
        "desc": desc,
        "content_proximity_score": proximity,
        "source": source,
        "thumbnail_url": f"https://thumb/{aid}.jpg",
        "tiktok_url": f"https://tiktok.com/@x/video/{aid}",
        "views": 68_000,
    }


def test_sanitize_drops_off_topic_embedded_tiles() -> None:
    refs = [
        _slim("111", "đồng hồ nam luxury", proximity=3),
        _slim("222", "mặt trông bị quá chưa", proximity=0),
    ]
    allowed = {"111", "222"}
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "text_vi": "prose",
                "embedded_tiles": [{"aweme_id": "222"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, allowed)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_sanitize_resolves_on_topic_tile_from_pool() -> None:
    refs = [
        _slim("111", "đồng hồ nam luxury", proximity=2),
        _slim("222", "unrelated viral", proximity=0),
    ]
    allowed = {"111", "222"}
    diag_vi = {
        "sections": [
            {
                "section_id": "niche_pattern",
                "embedded_tiles": [{"aweme_id": "111"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, allowed)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"
    assert "đồng hồ" in (tiles[0].get("caption_snippet") or "")


def test_sanitize_keeps_corpus_pool_tile_when_proximity_zero() -> None:
    refs = [_slim("111", "đồng hồ dây da", proximity=0, source="corpus")]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "111"}]}
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_inject_fallback_tile_when_gemini_omits_embedded_tiles() -> None:
    from getviews_pipeline.gemini import _inject_fallback_embedded_tiles

    refs = [_slim("111", "đồng hồ", proximity=0, source="corpus")]
    diag_vi = {
        "sections": [
            {"section_id": "hook_analysis", "text_vi": "prose", "embedded_tiles": []},
        ]
    }
    _inject_fallback_embedded_tiles(diag_vi, refs, {"111"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_sanitize_keeps_live_search_tile_when_proximity_zero() -> None:
    refs = [
        _slim("111", "đồng hồ nam dây da", proximity=0, source="live_search"),
        _slim("222", "unrelated beauty", proximity=0, source="live_search"),
    ]
    diag_vi = {
        "sections": [
            {
                "section_id": "hook_analysis",
                "embedded_tiles": [{"aweme_id": "111"}],
            }
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111", "222"})
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert tiles[0]["aweme_id"] == "111"


def test_repair_diagnosis_vi_embedded_tiles_injects_when_empty() -> None:
    refs = [_slim("111", "đồng hồ nam luxury", proximity=1)]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "text_vi": "prose", "embedded_tiles": []},
        ]
    }
    n = repair_diagnosis_vi_embedded_tiles(diag_vi, refs)
    assert n >= 1
    assert count_valid_embedded_tiles(diag_vi) >= 1


def test_embed_contract_version_constant() -> None:
    assert EMBED_CONTRACT_VERSION >= 1


def test_validate_citations_invokes_tile_sanitize() -> None:
    refs = [_slim("111", "match caption keyword đồng hồ", proximity=1)]
    diag_vi = {
        "sections": [
            {
                "section_id": "diagnosis",
                "embedded_tiles": [{"aweme_id": "111", "caption_snippet": "wrong"}],
            }
        ]
    }
    _validate_diagnosis_vi_citations(diag_vi, {"111"}, refs)
    tiles = diag_vi["sections"][0]["embedded_tiles"]
    assert len(tiles) == 1
    assert "đồng hồ" in (tiles[0].get("caption_snippet") or "")
