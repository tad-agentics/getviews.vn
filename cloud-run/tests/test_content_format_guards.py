"""Tests for foreign-reup detection and commerce format guards."""

from __future__ import annotations

from getviews_pipeline.content_format_guards import (
    detect_foreign_reup,
    guard_content_format,
    refresh_video_content_format,
)
from getviews_pipeline.corpus_ingest import _content_class_for, classify_format


def _analysis(transcript: str = "", *, topics: list[str] | None = None, **extra) -> dict:
    base: dict = {
        "audio_transcript": transcript,
        "topics": topics or [],
        "scenes": [{"type": "action"}],
        "tone": "entertaining",
    }
    base.update(extra)
    return base


def test_detect_foreign_reup_from_style_tag() -> None:
    assert detect_foreign_reup(_analysis(style_tags=["foreign_reup", "text_overlay_heavy"]))


def test_detect_foreign_reup_cjk_plus_vn_overlay() -> None:
    analysis = _analysis(
        "今天天气很好",
        text_overlays=[{"text": "Hôm nay trời đẹp quá nha"}],
    )
    assert detect_foreign_reup(analysis)


def test_guard_strips_haul_for_foreign_reup_with_vn_subtitle_commerce_words() -> None:
    """VN subtitle «mua về» on Chinese footage must not become haul."""
    analysis = _analysis(
        "这个女孩很厉害",
        topics=["china", "drama"],
        text_overlays=[{"text": "Cô gái này mua về nhà thử ngay"}],
        style_tags=["foreign_reup", "text_overlay_heavy"],
        commerce_intent={"product_price_tier": "not_commerce"},
        niche_classification={"format_axis": "react_commentary"},
    )
    fmt = classify_format(analysis, legacy_niche_id=13)
    assert fmt != "haul"
    assert fmt in ("highlight", "other", "comedy_skit", "storytelling")


def test_weak_mua_ve_without_commerce_is_not_haul() -> None:
    analysis = _analysis("Mình mua về nhà thử ngay", commerce_intent={"product_price_tier": "not_commerce"})
    assert classify_format(analysis, legacy_niche_id=3) != "haul"


def test_genuine_haul_unbox_still_matches() -> None:
    assert classify_format(_analysis("Mở hộp Shopee haul đồ skincare"), 3) == "haul"


def test_guard_content_format_leaves_non_commerce_formats() -> None:
    assert guard_content_format("vlog", _analysis(style_tags=["foreign_reup"])) == "vlog"


def test_detect_foreign_reup_vn_dub_with_sub_caption_overlays() -> None:
    """Full VN dub (no CJK) + sub_caption overlays — CN reup pattern."""
    analysis = _analysis(
        "Cô gái này làm một việc không thể tin được trong video hôm nay",
        topics=["drama", "trung quốc"],
        text_overlays=[
            {"text": "Cô ấy thật sự giỏi", "overlay_style": "sub_caption"},
        ],
        style_tags=["voiceover_only", "text_overlay_heavy"],
        commerce_intent={"product_price_tier": "not_commerce"},
        niche_classification={"format_axis": "react_commentary"},
    )
    assert detect_foreign_reup(analysis)


def test_quoc_te_travel_alone_is_not_foreign_reup() -> None:
    """Native VN travel vlog — «quốc tế» alone must not trigger reup."""
    analysis = _analysis(
        "Hôm nay mình chia sẻ kinh nghiệm du lịch quốc tế",
        topics=["du lịch quốc tế", "travel"],
        text_overlays=[{"text": "Paris mùa thu thật đẹp"}],
        style_tags=["text_overlay_heavy", "vlog"],
        commerce_intent={"product_price_tier": "not_commerce"},
    )
    assert not detect_foreign_reup(analysis)


def test_refresh_video_content_format_updates_class_id() -> None:
    video = {"content_format": "haul", "content_class_id": 99}
    analysis = _analysis(
        "这个女孩很厉害",
        topics=["china"],
        text_overlays=[{"text": "Cô gái này mua về nhà thử"}],
        style_tags=["foreign_reup", "text_overlay_heavy"],
        commerce_intent={"product_price_tier": "not_commerce"},
        niche_classification={"format_axis": "react_commentary"},
    )
    fmt = refresh_video_content_format(video, analysis, niche_id=13)
    assert fmt != "haul"
    assert video["content_format"] == fmt
    expected_cc = _content_class_for(13, fmt)
    if expected_cc is not None:
        assert video["content_class_id"] == expected_cc
