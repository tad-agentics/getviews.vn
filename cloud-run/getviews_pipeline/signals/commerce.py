from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_CTA_OVERLAY_RE = re.compile(
    r"mua|inbox|link|shop|giá|order|đặt|cart|giỏ|shopee|tiktok\s*shop",
    re.IGNORECASE,
)
_PRICE_STRUCTURE_RE = re.compile(
    r"\d+\s*(k|tr|triệu|đ|%|vnd)|giá\s*\d|chỉ\s+\d",
    re.IGNORECASE,
)
_AUTHORITY_HOOK_TYPES = frozenset(
    {
        "bold_claim",
        "shock_stat",
        "social_proof",
        "controversy",
        "expose",
        "vach_tran",
        "comparison",
        "insider",
        "secret",
        "tips_value",
    }
)


def _as_commerce_dict(ua: dict) -> dict[str, Any]:
    raw = ua.get("commerce_intent")
    return raw if isinstance(raw, dict) else {}


def _is_commercial(ua: dict, ci: dict[str, Any]) -> bool:
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    # If Gemini populated commerce_intent at all, there is enough evidence to
    # run commerce analysis regardless of conversion_objective label.
    if ci:
        return True
    return False


def _verbal_cta_satisfied(ua: dict, ci: dict[str, Any]) -> bool:
    if ci:
        return bool(ci.get("verbal_cta_present"))
    return bool(str(ua.get("cta") or "").strip())


def _overlay_text(ua: dict[str, Any]) -> str:
    parts: list[str] = []
    for o in ua.get("text_overlays") or []:
        if isinstance(o, dict):
            parts.append(str(o.get("text") or ""))
        else:
            parts.append(str(o))
    return " ".join(parts)


def extract_commerce_silent_cta_signal(ctx: dict) -> list[Signal]:
    """P1 — CTA trên chữ nhưng không có lời nói."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    if not _is_commercial(ua, ci):
        return []
    if _verbal_cta_satisfied(ua, ci):
        return []
    overlay = _overlay_text(ua)
    if not _CTA_OVERLAY_RE.search(overlay):
        return []
    return [
        Signal(
            id="commerce_silent_cta",
            section_id="commerce",
            taxonomy_ref="§4.8.3",
            salience=0.76,
            claim=(
                "Có CTA trên chữ overlay nhưng thiếu lời kêu gọi — "
                "khán xem tắt tiếng dễ bỏ lỡ bước chuyển đổi."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="verbal_cta_present=false overlay_has_cta=true",
                    location="user_analysis.commerce_intent+text_overlays",
                )
            ],
            suggested_fix="Lồng 1 câu CTA voice trùng overlay (mua, inbox Shop, mã giảm).",
        )
    ]


def extract_commerce_price_tier_structure_signal(ctx: dict) -> list[Signal]:
    """P1 — có price tier nhưng thiếu cấu trúc giá trên clip."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    tier = str(ci.get("product_price_tier") or "").strip().lower()
    if not tier or tier in ("not_commerce", "none", "unknown"):
        return []
    if ci.get("price_structure_present") is True:
        return []
    blob = f"{ua.get('audio_transcript') or ''} {_overlay_text(ua)}"
    if _PRICE_STRUCTURE_RE.search(blob):
        return []
    return [
        Signal(
            id="commerce_price_tier_structure",
            section_id="commerce",
            taxonomy_ref="§4.8.3",
            salience=0.71,
            claim=(
                f"Tier giá `{tier}` nhưng clip thiếu neo giá rõ (số/%) trên overlay hoặc VO — "
                "khó kích FOMO mua."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"product_price_tier={tier} price_structure_present=false",
                    location="user_analysis.commerce_intent+transcript",
                )
            ],
            suggested_fix="Thêm 1 neo giá cụ thể (VD: 99K, -30%) trên chữ + lời nói trong 5s đầu.",
        )
    ]


def extract_conversion_objective_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    if not ci:
        return []
    if not _is_commercial(ua, ci):
        return []
    obj = str(ci.get("conversion_objective") or "entertainment_first").strip()
    promo = str(ua.get("promotion_type") or "organic").lower()
    if obj == "entertainment_first" and promo not in ("organic", ""):
        obj = promo
    return [
        Signal(
            id="commerce_conversion_objective",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=0.6,
            claim=f"Mục tiêu chuyển đổi: {obj} — cần CTA rõ khi có quan hệ thương mại.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"conversion_objective={obj}",
                    location="user_analysis.commerce_intent.conversion_objective",
                )
            ],
            suggested_fix=None,
        )
    ]


def extract_verbal_cta_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    if not ci:
        return []
    if not _is_commercial(ua, ci):
        return []
    if _verbal_cta_satisfied(ua, ci):
        return []
    return [
        Signal(
            id="commerce_verbal_cta_missing",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=0.80,
            claim="Thiếu lời kêu gọi hành động rõ trong giọng nói cho nội dung thương mại.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="verbal_cta_present=false",
                    location="user_analysis.commerce_intent.verbal_cta_present",
                )
            ],
            suggested_fix="Thêm một câu CTA cụ thể cuối VO (mua, lưu, inbox Shop…).",
        )
    ]


def extract_price_tier_hook_mismatch_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    tier = str(ci.get("product_price_tier") or "").lower()
    if tier != "under_150k":
        return []
    ha = ua.get("hook_analysis") or {}
    if not isinstance(ha, dict):
        return []
    ht = str(ha.get("hook_type") or "").lower()
    if ht not in _AUTHORITY_HOOK_TYPES:
        return []
    return [
        Signal(
            id="commerce_price_tier_hook_mismatch",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=0.70,
            claim="Giá entry thấp nhưng hook kiểu uy quyền/chứng cứ — lệch kỳ vọng xung đột giá.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"product_price_tier={tier} hook_type={ht}",
                    location="user_analysis.commerce_intent+hook_analysis",
                )
            ],
            suggested_fix="Cân nhắc hook FOMO/giá/trải nghiệm nhanh cho SP dưới 150k.",
        )
    ]


def extract_disclosure_signal(_ctx: dict) -> list[Signal]:
    """Disabled — commercial disclosure findings removed from video diagnosis."""
    return []


def extract_creator_type_consistency_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    if not ci:
        return []
    ctype = str(ci.get("creator_type") or "").lower()
    cc = ua.get("content_context") or {}
    if not isinstance(cc, dict):
        return []
    purpose = str(cc.get("content_purpose") or "").lower()
    role = str(cc.get("creator_role") or "").lower()

    mismatch = False
    detail = ""
    if ctype == "entertainment" and purpose == "sell":
        mismatch = True
        detail = "creator_type=entertainment vs content_purpose=sell"
    elif ctype == "entertainment" and role in ("expert", "tutorial_host"):
        mismatch = True
        detail = f"creator_type=entertainment vs creator_role={role}"

    if not mismatch:
        return []
    return [
        Signal(
            id="commerce_creator_type_inconsistent",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=0.5,
            claim="Vai người lên hình (commerce_intent) lệch với vai nội dung (content_context).",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=detail,
                    location="user_analysis.commerce_intent+content_context",
                )
            ],
            suggested_fix="Thống nhất persona: expert/KOS versus giải trí thuần.",
        )
    ]


def extract_legacy_promotion_signal(ctx: dict) -> list[Signal]:
    """When ``commerce_intent`` is absent, preserve Sprint-0 promotion_type + CTA heuristics."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    if _as_commerce_dict(ua):
        return []
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo in ("organic", ""):
        return []

    cta = str(ua.get("cta") or "").strip()
    out: list[Signal] = [
        Signal(
            id="commerce_promotion_detected",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=0.6,
            claim=f"Video mang tính hướng thương mại (promotion_type={promo}) — cần chấm CTA.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"promotion_type={promo}",
                    location="user_analysis.promotion_type",
                )
            ],
            suggested_fix="Rõ ràng CTA voice khi có brand/affiliate.",
        )
    ]
    if not cta:
        out.append(
            Signal(
                id="commerce_cta_missing",
                section_id="commerce",
                taxonomy_ref="§0",
                salience=0.78,
                claim="Thiếu lời kêu gọi hành động lồng tiếng rõ ràng cho tín hiệu thương mại.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="cta=null",
                        location="user_analysis.cta",
                    )
                ],
                suggested_fix="Thêm một câu CTA cụ thể cuối VO (mua, lưu, inbox Shop…).",
            )
        )
    return out


def extract_commerce_signals(ctx: dict) -> list[Signal]:
    """§0 commerce signals: structured ``commerce_intent`` + legacy ``promotion_type`` fallback."""
    merged: list[Signal] = []
    merged.extend(extract_conversion_objective_signal(ctx))
    merged.extend(extract_verbal_cta_signal(ctx))
    merged.extend(extract_commerce_silent_cta_signal(ctx))
    merged.extend(extract_commerce_price_tier_structure_signal(ctx))
    merged.extend(extract_price_tier_hook_mismatch_signal(ctx))
    merged.extend(extract_creator_type_consistency_signal(ctx))
    merged.extend(extract_legacy_promotion_signal(ctx))
    return merged
