from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_commerce_signals(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
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
