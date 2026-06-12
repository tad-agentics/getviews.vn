"""Video diagnosis addressing — third party vs viewer's own channel."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.analysis_addressing import (
    build_addressing_prompt_block,
    fetch_viewer_tiktok_handle,
    resolve_video_addressing_mode,
)
from getviews_pipeline.diagnose_parse import fallback_tile_narrative_vi
from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt


def test_resolve_third_party_when_no_viewer_handle() -> None:
    assert (
        resolve_video_addressing_mode(
            video_creator_handle="@creator",
            viewer_tiktok_handle=None,
        )
        == "third_party"
    )


def test_resolve_third_party_when_handles_differ() -> None:
    assert (
        resolve_video_addressing_mode(
            video_creator_handle="Creator",
            viewer_tiktok_handle="@other",
        )
        == "third_party"
    )


def test_resolve_viewer_own_when_handles_match() -> None:
    assert (
        resolve_video_addressing_mode(
            video_creator_handle="@Creator",
            viewer_tiktok_handle="creator",
        )
        == "viewer_own"
    )


def test_third_party_prompt_forbids_ban() -> None:
    block = build_addressing_prompt_block("third_party", creator_handle="@foo")
    assert "CẤM" in block
    assert "@foo" in block
    assert "video của bạn" in block


def test_fallback_tile_third_party_no_cua_ban() -> None:
    tile = {"hook_type": "question", "content_format": "tutorial"}
    text = fallback_tile_narrative_vi(tile, "hook_analysis", 1, "third_party")
    assert "của bạn" not in text.lower()
    assert "bạn cần" not in text.lower()


def test_v6_prompt_includes_addressing_mode_in_ctx() -> None:
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="skincare",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={"views": 1000},
        performance_tier="hit",
        channel_context=None,
        errors=None,
        wants_directions=False,
        addressing_mode="third_party",
        video_creator_handle="@peer",
    )
    assert "addressing_mode" in prompt
    assert "third_party" in prompt
    assert "ĐỐI TƯỢNG ĐỌC" in prompt


def test_v6_prompt_average_diagnosis_has_no_short_prose_cap() -> None:
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="skincare",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={"views": 1000},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
    )
    assert "SECTION diagnosis (tier=average" in prompt
    assert "≤90 từ" in prompt
    assert "ưu tiên 4 câu trong ngân sách ≤90 từ" in prompt
    assert "KHÔNG dùng câu chung «Được chọn vì format»" in prompt
    assert "≤50 từ" not in prompt


def test_fetch_viewer_tiktok_handle_reads_profile() -> None:
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"tiktok_handle": "@mine"},
    )
    assert fetch_viewer_tiktok_handle(sb, "user-uuid") == "@mine"
