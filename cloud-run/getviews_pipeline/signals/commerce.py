from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_AUTHORITY_HOOK_TYPES = frozenset(
    {"bold_claim", "shock_stat", "social_proof", "controversy"}
)


def _as_commerce_dict(ua: dict) -> dict[str, Any]:
    raw = ua.get("commerce_intent")
    return raw if isinstance(raw, dict) else {}


def _is_commercial(ua: dict, ci: dict[str, Any]) -> bool:
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    obj = str(ci.get("conversion_objective") or "entertainment_first").lower()
    return obj != "entertainment_first"


def _verbal_cta_satisfied(ua: dict, ci: dict[str, Any]) -> bool:
    if ci:
        return bool(ci.get("verbal_cta_present"))
    return bool(str(ua.get("cta") or "").strip())


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
            salience=0.62,
            claim=f"Mục tiêu chuyển đổi: {obj} — cần CTA và tiết lộ rõ khi có quan hệ thương mại.",
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


def extract_disclosure_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    promo = str(ua.get("promotion_type") or "organic").lower()
    if not _is_commercial(ua, ci):
        return []
    if ci:
        if ci.get("disclosure_present"):
            return []
        salience = 0.85
        loc = "user_analysis.commerce_intent.disclosure_present"
        quote = "disclosure_present=false"
    else:
        # Legacy row: flag when relationship likely but no structured disclosure.
        if promo not in ("brand_deal", "affiliate"):
            return []
        salience = 0.78
        loc = "user_analysis.promotion_type"
        quote = f"promotion_type={promo} (no commerce_intent.disclosure)"
    return [
        Signal(
            id="commerce_disclosure_missing",
            section_id="commerce",
            taxonomy_ref="§0",
            salience=salience,
            claim=(
                "Thương mại hiển nhiên nhưng thiếu tiết lộ rõ "
                "(#qc / giọng / chữ) — rủi ro Ad Law."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=quote,
                    location=loc,
                )
            ],
            suggested_fix="Thêm tiết lộ voice hoặc #qc / chữ overlay theo Khung an toàn quảng cáo.",
        )
    ]


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
            salience=0.52,
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
            salience=0.62,
            claim=f"Video mang tính thương mại (promotion_type={promo}) — cần chấm CTA và tiết lộ.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"promotion_type={promo}",
                    location="user_analysis.promotion_type",
                )
            ],
            suggested_fix="Rõ ràng CTA voice + tiết lộ quan hệ khi có brand/affiliate.",
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
    merged.extend(extract_price_tier_hook_mismatch_signal(ctx))
    merged.extend(extract_disclosure_signal(ctx))
    merged.extend(extract_creator_type_consistency_signal(ctx))
    merged.extend(extract_legacy_promotion_signal(ctx))
    return merged
