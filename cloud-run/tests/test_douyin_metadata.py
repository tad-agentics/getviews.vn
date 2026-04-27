"""D2b (2026-06-03) — Kho Douyin metadata + row-builder tests.

Pure-function tests with hand-built aweme dicts (no network, no DB).
Each test exercises one slice of ``build_douyin_corpus_row``:
identity, creator, metrics, hook, caption, translation handoff,
content-type, and the early-return paths (analysis errored, empty
aweme_id, missing translation).
"""

from __future__ import annotations

from typing import Any

import pytest

from getviews_pipeline.douyin_metadata import (
    _normalize_handle,
    _safe_engagement_rate,
    build_douyin_corpus_row,
    build_douyin_url,
    parse_douyin_metadata,
)
from getviews_pipeline.douyin_translator import CaptionTranslation


# ── Fixtures ─────────────────────────────────────────────────────────


def _aweme(**overrides: Any) -> dict[str, Any]:
    """Hand-built Douyin aweme_detail dict. The canonical Douyin web
    API shape — both EnsembleData and TikHub re-emit this envelope
    unchanged, so downstream metadata parsing is provider-agnostic.
    See ``tikhub_douyin.py`` for the live provider."""
    base: dict[str, Any] = {
        "aweme_id": "7350123456789",
        "desc": "睡前3件事 #养生 改变人生",
        "create_time": 1717000000,
        "text_extra": [
            {"hashtag_name": "养生"},
            {"hashtag_name": "晚间routine"},
            # Non-hashtag text_extra entries must be ignored.
            {"some_other_field": "noise"},
        ],
        "video": {
            "duration": 51_000,  # ms
            "play_addr_h264": {
                "url_list": ["https://cdn.douyin.test/video.mp4"],
            },
            "origin_cover": {
                "url_list": ["https://cdn.douyin.test/cover.jpg"],
            },
        },
        "statistics": {
            "play_count": 4_100_000,
            "digg_count": 412_000,
            "comment_count": 8_900,
            "share_count": 23_400,
            "collect_count": 124_000,
        },
        "author": {
            "unique_id": "sleepwell.life",
            "nickname": "Sleepwell Life",
            "follower_count": 980_000,
            "verification_type": 0,
        },
    }
    base.update(overrides)
    return base


def _analysis(**overrides: Any) -> dict[str, Any]:
    """Hand-built Gemini analysis dict matching analysis_core.analyze_aweme."""
    base: dict[str, Any] = {
        "analysis": {
            "scenes": [
                {"start": 0, "end": 3, "type": "face_to_camera"},
                {"start": 3, "end": 51, "type": "demo"},
            ],
            "hook_analysis": {
                "hook_type": "curiosity_gap",
                "hook_phrase": "睡前3件事 改变人生",
            },
            "transitions_per_second": 0.4,
        },
        "engagement_rate": 14.6,
        "metadata": {
            "metrics": {
                "views": 4_100_000,
                "likes": 412_000,
                "comments": 8_900,
                "shares": 23_400,
                "bookmarks": 124_000,
            },
        },
        "content_type": "video",
    }
    base.update(overrides)
    return base


# ── build_douyin_url ─────────────────────────────────────────────────


def test_build_douyin_url_canonical_format() -> None:
    assert build_douyin_url("7350123456789") == (
        "https://www.douyin.com/video/7350123456789"
    )


def test_build_douyin_url_strips_whitespace() -> None:
    assert build_douyin_url("  7350123456789 \n") == (
        "https://www.douyin.com/video/7350123456789"
    )


def test_build_douyin_url_handles_empty_id() -> None:
    """Should still produce a (broken) URL — the ingest pipeline
    short-circuits before calling this on empty ids; defensive only."""
    assert build_douyin_url("") == "https://www.douyin.com/video/"


# ── _normalize_handle ────────────────────────────────────────────────


def test_normalize_handle_strips_at_and_lowercases() -> None:
    assert _normalize_handle("@SleepWell.Life") == "sleepwell.life"


def test_normalize_handle_handles_none_and_empty() -> None:
    assert _normalize_handle(None) == "unknown"
    assert _normalize_handle("") == "unknown"


def test_normalize_handle_collapses_internal_whitespace() -> None:
    assert _normalize_handle("@hello world") == "helloworld"


# ── _safe_engagement_rate (with saves) ───────────────────────────────


def test_engagement_rate_uses_er_from_analysis_when_positive() -> None:
    out = _safe_engagement_rate(
        er_from_analysis=14.6,
        views=100, likes=0, comments=0, shares=0, saves=0,
    )
    assert out == 14.6


def test_engagement_rate_falls_back_to_computed_when_analysis_zero() -> None:
    """When the Gemini-reported ER is 0/None, recompute from raw counts
    (Douyin includes saves in the numerator)."""
    out = _safe_engagement_rate(
        er_from_analysis=None,
        views=1000,
        likes=100, comments=10, shares=10, saves=80,
    )
    # (100 + 10 + 10 + 80) / 1000 * 100 = 20.0
    assert out == 20.0


def test_engagement_rate_returns_zero_on_zero_views() -> None:
    out = _safe_engagement_rate(
        er_from_analysis=None,
        views=0, likes=10, comments=10, shares=10, saves=10,
    )
    assert out == 0.0


def test_engagement_rate_caps_at_100() -> None:
    out = _safe_engagement_rate(
        er_from_analysis=None,
        views=10, likes=100, comments=100, shares=100, saves=100,
    )
    assert out == 100.0


# ── parse_douyin_metadata ────────────────────────────────────────────


def test_parse_douyin_metadata_delegates_to_tiktok_parser() -> None:
    """Douyin awemes share the schema with TikTok per ED docs — the
    re-exported parser must produce a valid VideoMetadata for both."""
    out = parse_douyin_metadata(_aweme())
    assert out.video_id == "7350123456789"
    assert out.author.username == "sleepwell.life"
    assert out.metrics.views == 4_100_000
    # Hashtags from text_extra
    assert "养生" in out.hashtags
    assert "晚间routine" in out.hashtags


# ── build_douyin_corpus_row — happy path ─────────────────────────────


def test_row_carries_identity_and_url() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["video_id"] == "7350123456789"
    assert row["douyin_url"] == "https://www.douyin.com/video/7350123456789"
    assert row["niche_id"] == 1
    assert row["content_type"] == "video"


def test_row_carries_creator_fields() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["creator_handle"] == "sleepwell.life"
    assert row["creator_name"] == "Sleepwell Life"
    assert row["creator_followers"] == 980_000


def test_row_carries_media_urls() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["thumbnail_url"] == "https://cdn.douyin.test/cover.jpg"
    assert row["video_url"] == "https://cdn.douyin.test/video.mp4"
    assert row["frame_urls"] == []  # D2c fills


def test_row_carries_engagement_metrics_with_saves() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["views"] == 4_100_000
    assert row["likes"] == 412_000
    assert row["saves"] == 124_000
    # ER prefers the analysis value when positive.
    assert row["engagement_rate"] == 14.6


def test_row_carries_posted_at_iso_when_create_time_set() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["posted_at"] is not None
    assert row["posted_at"].endswith("+00:00")  # UTC ISO


def test_row_posted_at_none_when_create_time_missing() -> None:
    aweme = _aweme()
    aweme.pop("create_time")
    aweme.pop("createTime", None)
    row = build_douyin_corpus_row(aweme, _analysis(), niche_id=1)
    assert row is not None
    assert row["posted_at"] is None


def test_row_carries_video_duration_from_last_scene_end() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["video_duration"] == 51.0


def test_row_carries_hook_type_and_phrase() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["hook_type"] == "curiosity_gap"
    assert row["hook_phrase"] == "睡前3件事 改变人生"


def test_row_carries_chinese_caption_and_hashtags() -> None:
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["title_zh"] == "睡前3件事 #养生 改变人生"
    # Hashtags get the leading # prefix added so they read like the design.
    assert row["hashtags_zh"] == ["#养生", "#晚间routine"]


# ── build_douyin_corpus_row — translation handoff ────────────────────


def test_row_title_vi_and_sub_vi_filled_from_translation() -> None:
    translation = CaptionTranslation(
        title_vi="Trước khi ngủ làm 3 việc",
        sub_vi="3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",
    )
    row = build_douyin_corpus_row(
        _aweme(), _analysis(), niche_id=1, translation=translation,
    )
    assert row is not None
    assert row["title_vi"] == "Trước khi ngủ làm 3 việc"
    assert row["sub_vi"] == "3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác"


def test_row_title_vi_and_sub_vi_none_when_translation_missing() -> None:
    """Translator returned None (Gemini failure / empty desc) — row
    still lands so D3 synth can re-attempt translation later."""
    row = build_douyin_corpus_row(_aweme(), _analysis(), niche_id=1)
    assert row is not None
    assert row["title_vi"] is None
    assert row["sub_vi"] is None


# ── build_douyin_corpus_row — error paths ────────────────────────────


def test_row_returns_none_when_analysis_has_error() -> None:
    bad_analysis = {"error": "gemini timeout", "metadata": {}}
    row = build_douyin_corpus_row(_aweme(), bad_analysis, niche_id=1)
    assert row is None


def test_row_returns_none_when_analysis_missing_analysis_key() -> None:
    bad_analysis: dict[str, Any] = {"metadata": {}}
    row = build_douyin_corpus_row(_aweme(), bad_analysis, niche_id=1)
    assert row is None


def test_row_returns_none_when_aweme_id_empty() -> None:
    aweme = _aweme(aweme_id="")
    row = build_douyin_corpus_row(aweme, _analysis(), niche_id=1)
    assert row is None


def test_row_handles_minimal_aweme_without_optional_fields() -> None:
    """Defensive: missing music, follower count, scenes shouldn't blow
    up the row builder. Returns a row with the optional fields None."""
    aweme = {
        "aweme_id": "1",
        "desc": "测试",
        "video": {"play_addr_h264": {"url_list": ["https://cdn/v.mp4"]}},
        "statistics": {"play_count": 100},
        "author": {"unique_id": "alice"},
    }
    analysis = {
        "analysis": {"scenes": [], "hook_analysis": {}},
        "metadata": {"metrics": {}},
        "content_type": "video",
    }
    row = build_douyin_corpus_row(aweme, analysis, niche_id=1)
    assert row is not None
    assert row["video_id"] == "1"
    assert row["creator_followers"] is None
    assert row["video_duration"] is None
    assert row["hook_type"] is None
    assert row["hook_phrase"] is None
    assert row["thumbnail_url"] is None
    assert row["hashtags_zh"] == []
