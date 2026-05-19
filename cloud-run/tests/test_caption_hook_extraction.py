"""Caption vs in-video hook extraction (Curnon-style tagline overlay)."""

from __future__ import annotations

from getviews_pipeline.creator_blocklist import niche_override_for_handle
from getviews_pipeline.live_niche import caption_for_niche_resolution
from getviews_pipeline.prompts import (
    build_tiktok_caption_extraction_prefix,
    merge_extraction_supplemental_prefixes,
)


def test_build_tiktok_caption_extraction_prefix_includes_desc_and_tags() -> None:
    prefix = build_tiktok_caption_extraction_prefix(
        "Bạn có biết vì sao nhẫn xoay lại hot?\nComing soon - 19.05.2026",
        ["curnon", "newcollection"],
    )
    assert prefix is not None
    assert "CAPTION_TIKTOK" in prefix
    assert "Bạn có biết" in prefix
    assert "#curnon" in prefix


def test_merge_extraction_supplemental_prefixes_orders_asr_then_caption() -> None:
    merged = merge_extraction_supplemental_prefixes(
        "ASR_BLOCK",
        build_tiktok_caption_extraction_prefix("Caption line", []),
    )
    assert merged is not None
    assert merged.index("ASR_BLOCK") < merged.index("CAPTION_TIKTOK")


def test_curnon_creator_niche_override() -> None:
    assert niche_override_for_handle("@curnon.official") == 3
    assert niche_override_for_handle("CURNON.OFFICIAL") == 3


def test_caption_for_niche_resolution_includes_challenges() -> None:
    aweme = {
        "desc": "Review trang sức",
        "challenges": [{"title": "thoitrang"}, {"title": "phukien"}],
    }
    cap = caption_for_niche_resolution(aweme)
    assert "Review trang sức" in cap
    assert "thoitrang" in cap
