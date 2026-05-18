"""§4 Script structure — affiliate five-phase + livestream funnel (Sprint 7)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_PHASE_KEYS = (
    "hook_attention",
    "product_showcase",
    "usage_demo",
    "social_proof",
    "closing_cta",
)
_PHASE_LABELS_VI = {
    "hook_attention": "hook thu hút",
    "product_showcase": "showcase sản phẩm",
    "usage_demo": "demo dùng thử",
    "social_proof": "bằng chứng xã hội / review",
    "closing_cta": "CTA chốt",
}


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    return ua if isinstance(ua, dict) else {}


def _commerce_intent(ctx: dict) -> dict[str, Any]:
    ua = _ua(ctx)
    ci = ua.get("commerce_intent") or {}
    return ci if isinstance(ci, dict) else {}


def extract_5_phase_affiliate_signal(ctx: dict) -> list[Signal]:
    ci = _commerce_intent(ctx)
    obj = str(ci.get("conversion_objective") or "").strip().lower()
    if obj not in ("shop_direct", "affiliate_shopee"):
        return []
    ua = _ua(ctx)
    phases_raw = ua.get("affiliate_script_phases")
    if not isinstance(phases_raw, dict):
        return []
    vals: list[bool | None] = []
    for k in _PHASE_KEYS:
        v = phases_raw.get(k)
        if v is True:
            vals.append(True)
        elif v is False:
            vals.append(False)
        else:
            vals.append(None)
    unknown_ct = sum(1 for v in vals if v is None)
    if unknown_ct >= 4:
        return []
    false_ct = sum(1 for v in vals if v is False)
    if false_ct < 2:
        return []
    missing_names = [
        _PHASE_LABELS_VI[k] for k, v in zip(_PHASE_KEYS, vals, strict=True) if v is False
    ]
    detail = ", ".join(missing_names[:4])
    return [
        Signal(
            id="script_affiliate_five_phase_gap",
            section_id="script_structure",
            taxonomy_ref="§4",
            salience=0.75,
            claim=(
                f"Công thức affiliate 5 pha thiếu ít nhất hai lớp rõ — các phần yếu: {detail}."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"affiliate_script_phases={phases_raw!r}",
                    location="user_analysis.affiliate_script_phases",
                ),
            ],
            suggested_fix=(
                "Lắp lần lượt: hook có payoff ngắn → cận sản phẩm → demo 5–12s → 1 bằng chứng "
                "comment/UGC → CTA nói rõ lợi ích + bước mua."
            ),
        )
    ]


def extract_livestream_funnel_signal(ctx: dict) -> list[Signal]:
    ci = _commerce_intent(ctx)
    obj = str(ci.get("conversion_objective") or "").strip().lower()
    if obj != "livestream_funnel":
        return []
    ua = _ua(ctx)
    bal = str(ua.get("livestream_funnel_demo") or "").strip().lower()
    if bal != "over_complete":
        return []
    return [
        Signal(
            id="script_livestream_demo_too_complete",
            section_id="script_structure",
            taxonomy_ref="§4",
            salience=0.6,
            claim=(
                "Clip hướng funnel live nhưng demo đủ trọn vẹn — khán giả có thể không cần "
                "vào live, giảm hiệu quả kéo phòng."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="livestream_funnel_demo=over_complete",
                    location="user_analysis.livestream_funnel_demo",
                ),
            ],
            suggested_fix="Giữ payoff mở: 1 chi tiết kỹ thuật / deal chỉ giải trong live; tránh hướng dẫn end-to-end.",
        )
    ]


def extract_script_signals(ctx: dict) -> list[Signal]:
    return [
        *extract_5_phase_affiliate_signal(ctx),
        *extract_livestream_funnel_signal(ctx),
    ]
