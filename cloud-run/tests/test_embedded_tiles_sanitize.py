"""Embedded reference tiles must resolve from the synthesis pool with content proximity."""

from __future__ import annotations

from getviews_pipeline.gemini import (
    _sanitize_diagnosis_embedded_tiles,
    _validate_diagnosis_vi_citations,
)


def _slim(aid: str, desc: str, *, proximity: int) -> dict:
    return {
        "aweme_id": aid,
        "desc": desc,
        "content_proximity_score": proximity,
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
    assert tiles == []


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


def test_sanitize_clears_all_tiles_when_no_proximity_match() -> None:
    refs = [_slim("111", "generic beauty", proximity=0)]
    diag_vi = {
        "sections": [
            {"section_id": "diagnosis", "embedded_tiles": [{"aweme_id": "111"}]}
        ]
    }
    _sanitize_diagnosis_embedded_tiles(diag_vi, refs, {"111"})
    assert diag_vi["sections"][0]["embedded_tiles"] == []


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
