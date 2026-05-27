"""§5 Editing — color grading + on-screen text design (diagnosis-first Sprint 8)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_BROLL_SCENE_TYPES = frozenset({"broll", "ambient", "lifestyle_b_roll", "b_roll"})
_NICHES_EXPECT_HIGH_KEY = frozenset({"beauty", "fashion"})
_MIN_NICHE_SAMPLE = 30


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


def _user_transitions_per_second(ua: dict[str, Any]) -> float | None:
    raw = ua.get("transitions_per_second")
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val >= 0 else None


def _transitions_p25_p75(nm: dict[str, Any]) -> tuple[float | None, float | None]:
    p25_raw = nm.get("p25_transitions_per_second")
    p75_raw = nm.get("p75_transitions_per_second")
    if p25_raw is not None and p75_raw is not None:
        try:
            p25 = float(p25_raw)
            p75 = float(p75_raw)
            if p75 > p25:
                return p25, p75
        except (TypeError, ValueError):
            pass

    avg_raw = nm.get("avg_transitions_per_second")
    if avg_raw is None:
        return None, None
    try:
        avg = float(avg_raw)
    except (TypeError, ValueError):
        return None, None
    if avg <= 0:
        return None, None
    return avg * 0.75, avg * 1.25


def extract_editing_cut_pace_outlier_signal(ctx: dict) -> list[Signal]:
    """P1 — transitions_per_second outside niche p25/p75 band."""
    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    ua = _ua(ctx)
    tps = _user_transitions_per_second(ua)
    if tps is None:
        return []

    p25, p75 = _transitions_p25_p75(nm)
    if p25 is None or p75 is None:
        return []

    if p25 <= tps <= p75:
        return []

    if tps < p25:
        claim = (
            f"Tốc độ cắt {tps:.2f}/s dưới p25 ngách ({p25:.2f}/s) — "
            "video chậm hơn cohort cùng format."
        )
        fix = "Tăng nhịp cắt cảnh nhanh (jump-cut) hoặc chèn B-roll xen kẽ để khớp với nhịp độ của ngách."
    else:
        claim = (
            f"Tốc độ cắt {tps:.2f}/s trên p75 ngách ({p75:.2f}/s) — "
            "có thể gây mỏi mắt hoặc khó theo dõi trên mobile."
        )
        fix = "Giữ 1–2 beat dài hơn giữa các cut; tránh cắt liên tục >p75 ngách."

    return [
        Signal(
            id="editing_cut_pace_outlier",
            section_id="editing",
            taxonomy_ref="§5",
            salience=0.62,
            claim=claim,
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"transitions_per_second={tps:.3f} p25={p25:.3f} p75={p75:.3f}",
                    location="user_analysis.transitions_per_second+niche_meta",
                )
            ],
            suggested_fix=fix,
        )
    ]


def extract_editing_broll_ratio_low_signal(ctx: dict) -> list[Signal]:
    """P1 — tỷ lệ B-roll thấp so mix scene."""
    ua = _ua(ctx)
    scenes = ua.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 3:
        return []
    typed = [s for s in scenes if isinstance(s, dict)]
    if len(typed) < 3:
        return []
    broll_n = sum(
        1
        for s in typed
        if str(s.get("type") or s.get("subject") or "").lower().replace("-", "_") in _BROLL_SCENE_TYPES
    )
    ratio = broll_n / len(typed)
    if ratio >= 0.18:
        return []
    return [
        Signal(
            id="editing_broll_ratio_low",
            section_id="editing",
            taxonomy_ref="§5",
            salience=0.54,
            claim=(
                f"B-roll chỉ {broll_n}/{len(typed)} scene ({ratio:.0%}) — "
                "visual monotonous, khó giữ mắt trên mobile."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"broll_scenes={broll_n} total_scenes={len(typed)}",
                    location="user_analysis.scenes",
                )
            ],
            suggested_fix="Xen 2–3 cận sản phẩm/hành động giữa talking-head để tăng nhịp visual.",
        )
    ]


def extract_editing_signals(ctx: dict) -> list[Signal]:
    return [
        *extract_color_grading_signal(ctx),
        *extract_text_overlay_design_signal(ctx),
        *extract_editing_cut_pace_outlier_signal(ctx),
        *extract_editing_broll_ratio_low_signal(ctx),
    ]
