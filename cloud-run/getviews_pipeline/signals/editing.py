"""§5 Editing — color grading + on-screen text design (diagnosis-first Sprint 8)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_NICHES_EXPECT_HIGH_KEY = frozenset({"beauty", "fashion"})


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis")
    return ua if isinstance(ua, dict) else {}


def _creator_niche_slug(ua: dict[str, Any]) -> str:
    nc = ua.get("niche_classification")
    if not isinstance(nc, dict):
        return ""
    return str(nc.get("creator_niche_slug") or "").strip().lower()


def extract_color_grading_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    style = str(ua.get("color_grading_style") or "").strip().lower()
    if not style or style in ("unknown", "neutral"):
        return []
    niche = _creator_niche_slug(ua)
    mismatch = False
    if style == "over_processed":
        mismatch = True
    elif niche in _NICHES_EXPECT_HIGH_KEY and style == "desaturated_serious":
        mismatch = True
    if not mismatch:
        return []
    return [
        Signal(
            id="editing_color_grading_niche_mismatch",
            section_id="editing",
            taxonomy_ref="§5",
            salience=0.45,
            claim=(
                f"Tông màu ({style}) lệch chuẩn thẩm mỹ ngách hiện tại — "
                f"dễ trông lạc hậu hoặc quá xử lý."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"color_grading_style={style} creator_niche_slug={niche or 'n/a'}",
                    location="video_extraction",
                ),
            ],
            suggested_fix=(
                "Thử preset sáng, da ấm hoặc high-key nhẹ cho beauty/fashion; tránh desat quá mức hoặc HDR giả."
            ),
        )
    ]


def _commerce_not_entertainment(ua: dict[str, Any]) -> bool:
    ci = ua.get("commerce_intent")
    if not isinstance(ci, dict):
        return False
    obj = str(ci.get("conversion_objective") or "").strip().lower()
    return bool(obj and obj != "entertainment_first")


def extract_text_overlay_design_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    tier = str(ua.get("text_overlay_font_size_tier") or "").strip().lower()
    ce = ua.get("text_overlay_color_emphasis")
    commerce = _commerce_not_entertainment(ua)
    if tier == "small":
        trigger = True
    elif tier == "medium" and commerce and ce is not True:
        trigger = True
    else:
        trigger = False
    if not trigger:
        return []
    return [
        Signal(
            id="editing_text_overlay_readability",
            section_id="editing",
            taxonomy_ref="§5",
            salience=0.4,
            claim=(
                "Chữ overlay nhỏ hoặc thiếu nhấn màu trên mobile — giảm đọc CTA và giá khi cuộn nhanh."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"text_overlay_font_size_tier={tier} text_overlay_color_emphasis={ce}",
                    location="video_extraction",
                ),
            ],
            suggested_fix=(
                "Tăng cỡ chữ primary; tô 1–2 từ khóa (giá, %) màu tương phản; giữ line ≤6–8 chữ/dòng."
            ),
        )
    ]


def extract_editing_signals(ctx: dict) -> list[Signal]:
    return [*extract_color_grading_signal(ctx), *extract_text_overlay_design_signal(ctx)]
