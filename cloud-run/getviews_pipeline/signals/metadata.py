"""§1 Metadata — safe zone + account heuristics (diagnosis-first Sprint 8)."""

from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_MIN_NICHE_SAMPLE = 30


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


def extract_hashtag_volume_gap_signal(ctx: dict) -> list[Signal]:
    """P1 — hashtag_count lệch avg ngách."""
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    nm = ctx.get("niche_meta") if isinstance(ctx.get("niche_meta"), dict) else {}
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    raw_count = st.get("hashtag_count")
    if raw_count is None:
        tags_raw = str(st.get("hashtags") or st.get("hashtag_string") or "")
        tags = re.findall(
            r"#?([\wĐđàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+)",
            tags_raw,
            re.UNICODE,
        )
        count = len(tags)
    else:
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            return []

    avg_raw = nm.get("avg_hashtag_count")
    if avg_raw is None:
        return []
    try:
        avg = float(avg_raw)
    except (TypeError, ValueError):
        return []
    if avg <= 0:
        return []

    ratio = count / avg
    if 0.6 <= ratio <= 1.6:
        return []

    if ratio < 0.6:
        claim = (
            f"Chỉ {count} hashtag so TB ngách ~{avg:.1f} — thiếu tín hiệu phân loại subniche."
        )
        fix = "Thêm 2–4 hashtag cụ thể (sản phẩm, pain, địa phương) thay generic."
    else:
        claim = (
            f"{count} hashtag vượt TB ngách ~{avg:.1f} — dễ loãng tín hiệu tìm kiếm."
        )
        fix = "Giữ 4–7 hashtag; ưu tiên 2–3 tag ngách + 1–2 tag trend."

    return [
        Signal(
            id="metadata_hashtag_volume_gap",
            section_id="metadata",
            taxonomy_ref="§1",
            salience=0.58,
            claim=claim,
            evidence=[
                Evidence(
                    type="niche_norms_pct",
                    quote=f"hashtag_count={count} niche_avg={avg:.2f}",
                    location="user_stats+niche_meta.avg_hashtag_count",
                )
            ],
            suggested_fix=fix,
        )
    ]


def extract_caption_density_signal(ctx: dict) -> list[Signal]:
    """P1 — caption mỏng khi ngách có pct_has_caption_text cao."""
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    nm = ctx.get("niche_meta") if isinstance(ctx.get("niche_meta"), dict) else {}
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    pct_raw = nm.get("pct_has_caption_text")
    if pct_raw is None:
        return []
    try:
        pct = float(pct_raw)
    except (TypeError, ValueError):
        return []
    if pct < 55.0:
        return []

    caption = str(st.get("caption") or "").strip()
    cap_len = len(caption)
    if cap_len >= 80:
        return []

    return [
        Signal(
            id="metadata_caption_density",
            section_id="metadata",
            taxonomy_ref="§1",
            salience=0.64,
            claim=(
                f"Caption {cap_len} ký tự trong khi ~{pct:.0f}% video ngách có text caption "
                "— mỏng hơn chuẩn khả năng được tìm thấy."
            ),
            evidence=[
                Evidence(
                    type="niche_norms_pct",
                    quote=f"caption_len={cap_len} pct_has_caption_text={pct:.1f}",
                    location="user_stats.caption+niche_meta",
                )
            ],
            suggested_fix="Mở rộng caption ≥100 ký tự: hook + từ khóa ngách + CTA nhẹ.",
        )
    ]


def extract_metadata_signals(ctx: dict) -> list[Signal]:
    return [
        *extract_safe_zone_signal(ctx),
        *extract_account_type_signal(ctx),
        *extract_hashtag_volume_gap_signal(ctx),
        *extract_caption_density_signal(ctx),
    ]
