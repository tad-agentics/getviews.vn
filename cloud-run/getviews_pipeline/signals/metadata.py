"""§1 Metadata — safe zone + account heuristics (diagnosis-first Sprint 8)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis")
    return ua if isinstance(ua, dict) else {}


def extract_safe_zone_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    raw = ua.get("safe_zone_status")
    if raw is None or raw == "":
        return []
    if str(raw).strip().lower() != "bottom_overlay_risk":
        return []
    return [
        Signal(
            id="metadata_safe_zone_bottom_risk",
            section_id="metadata",
            taxonomy_ref="§1",
            salience=0.6,
            claim=(
                "Chữ hoặc CTA quan trọng nằm sát vùng dưới khung — dễ chồng lên UI giỏ/Shop, "
                "giảm đọc và tap."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="safe_zone_status=bottom_overlay_risk",
                    location="video_extraction",
                ),
            ],
            suggested_fix=(
                "Đẩy giá/CTA lên vùng giữa hoặc trên 50% khung; tránh đặt neo giá sát mép dưới."
            ),
        )
    ]


def extract_account_type_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    if str(ua.get("tiktok_account_type_heuristic") or "").strip().lower() != "business":
        return []
    if ua.get("trending_vpop_sound") is not True:
        return []
    return [
        Signal(
            id="metadata_business_vpop_cml_friction",
            section_id="metadata",
            taxonomy_ref="§1",
            salience=0.55,
            claim=(
                "Tài khoản business + nhạc V-pop trending — rủi ro mute/strip hoặc giới hạn CML "
                "khi scale quảng cáo."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="tiktok_account_type_heuristic=business trending_vpop_sound=true",
                    location="video_extraction",
                ),
            ],
            suggested_fix=(
                "Ưu tiên nhạc CML/original có quyền rõ khi chạy ads; giữ V-pop chỉ khi chấp nhận rủi ro."
            ),
        )
    ]


def extract_metadata_signals(ctx: dict) -> list[Signal]:
    return [*extract_safe_zone_signal(ctx), *extract_account_type_signal(ctx)]
