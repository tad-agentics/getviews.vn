from __future__ import annotations

import logging
import re

from getviews_pipeline.corpus_boost_suspect import (
    classify_boost_suspect,
    boost_percentiles_from_niche_intel,
)
from getviews_pipeline.signals.base import Evidence, Signal

logger = logging.getLogger(__name__)

_GENERIC_HASHTAGS = frozenset(
    {
        "fyp",
        "foryou",
        "foryoupage",
        "viral",
        "trending",
        "xuhuong",
        "tiktok",
        "learnontiktok",
    }
)


def extract_distribution_signals(ctx: dict) -> list[Signal]:
    stats = ctx.get("user_stats") or {}
    caption = str(stats.get("caption") or "").strip()
    cap_len = len(caption)
    tags_raw = str(stats.get("hashtags") or stats.get("hashtag_string") or "")
    tags = [t.lower().lstrip("#") for t in re.findall(r"#?([\wĐđàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+)", tags_raw, re.UNICODE)]

    out: list[Signal] = []
    if cap_len > 0 and cap_len < 60:
        out.append(
            Signal(
                id="caption_thin",
                section_id="distribution",
                taxonomy_ref="§meta",
                salience=0.72,
                claim=f"Caption chỉ {cap_len} ký tự — mỏng hơn chuẩn discoverability.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=f"caption_len={cap_len}",
                        location="user_stats.caption",
                    )
                ],
                suggested_fix="Mở rộng caption ≥100 ký tự với từ khóa ngách cụ thể.",
            )
        )

    if tags:
        generic_n = sum(1 for t in tags if t in _GENERIC_HASHTAGS)
        if generic_n >= max(3, len(tags) - 1):
            out.append(
                Signal(
                    id="hashtag_generic_cluster",
                    section_id="distribution",
                    taxonomy_ref="§meta",
                    salience=0.68,
                    claim="Hashtag chủ yếu generic — thuật toán khó phân loại ngách.",
                    evidence=[
                        Evidence(
                            type="user_analysis_field",
                            quote=f"hashtags={tags[:12]}",
                            location="user_stats",
                        )
                    ],
                    suggested_fix="Thay 2–4 hashtag generic bằng hashtag chỉ rõ subniche.",
                )
            )

    music_origin = str(stats.get("music_origin") or "").lower()
    if music_origin == "original":
        out.append(
            Signal(
                id="sound_original",
                section_id="distribution",
                taxonomy_ref="§6",
                salience=0.52,
                claim="Nhạc original — kiểm tra có đang bỏ lỡ sound trending ngách.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="music_origin=original",
                        location="user_stats",
                    )
                ],
                suggested_fix=None,
            )
        )

    return out


def _user_stats(ctx: dict) -> dict:
    us = ctx.get("user_stats")
    return us if isinstance(us, dict) else {}


def _niche_meta(ctx: dict) -> dict:
    nm = ctx.get("niche_meta")
    return nm if isinstance(nm, dict) else {}


def extract_boost_views_er_mismatch_signal(ctx: dict) -> list[Signal]:
    us = _user_stats(ctx)
    views = int(us.get("views") or 0)
    if views <= 0:
        return []

    comments = int(us.get("comments") or 0)
    er = us.get("engagement_rate")
    try:
        er_f = float(er or 0)
    except (TypeError, ValueError):
        er_f = 0.0
    if er_f <= 1.0:
        er_f *= 100.0

    pct = boost_percentiles_from_niche_intel(_niche_meta(ctx))
    result = classify_boost_suspect(
        views=views,
        er=er_f,
        comments=comments,
        percentiles=pct,
        hard_reject_enabled=False,
    )
    if result.attribution not in ("suspect_medium", "suspect_low"):
        return []

    return [
        Signal(
            id="boost_views_er_mismatch",
            section_id="boost_attribution",
            taxonomy_ref="§4.7 M3",
            salience=0.84 if result.attribution == "suspect_medium" else 0.72,
            claim=(
                f"Có dấu hiệu view cao ({views:,}) nhưng ER/comments mỏng so ngách "
                f"({result.attribution}) — có thể skew ads/seeding, không khẳng định boost chắc."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"views={views} er={er_f:.2f} attribution={result.attribution}",
                    location="user_stats+niche_meta",
                )
            ],
            suggested_fix="So sánh hook/ER organic trước khi scale ads; kiểm tra comment thật.",
        )
    ]


def extract_boost_breakout_low_engagement_signal(ctx: dict) -> list[Signal]:
    us = _user_stats(ctx)
    bm_raw = us.get("breakout_multiplier") or us.get("target_vs_creator_median")
    if bm_raw is None:
        return []
    try:
        bm = float(bm_raw)
    except (TypeError, ValueError):
        return []
    if bm < 1.5:
        return []

    er = us.get("engagement_rate")
    try:
        er_f = float(er or 0)
    except (TypeError, ValueError):
        return []
    if er_f <= 1.0:
        er_f *= 100.0

    pct = boost_percentiles_from_niche_intel(_niche_meta(ctx))
    if er_f >= pct.p25_er:
        return []

    return [
        Signal(
            id="boost_breakout_low_engagement",
            section_id="boost_attribution",
            taxonomy_ref="§4.7 M3",
            salience=0.78,
            claim=(
                f"Breakout ×{bm:.1f} so median kênh nhưng ER {er_f:.1f}% dưới p25 ngách "
                f"(~{pct.p25_er:.1f}%) — có dấu hiệu view không kéo tương tác chất."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"breakout_multiplier={bm:.2f} er={er_f:.2f} p25_er={pct.p25_er:.2f}",
                    location="user_stats.breakout_multiplier+niche_meta",
                )
            ],
            suggested_fix="Kiểm tra nguồn traffic — ưu tiên hook giữ ER trước khi đẩy view.",
        )
    ]


def extract_live_boost_attribution_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_boost_views_er_mismatch_signal(ctx))
    out.extend(extract_boost_breakout_low_engagement_signal(ctx))
    if out:
        logger.info(
            "[signals/distribution] boost_attribution fired ids=%s",
            [s.id for s in out],
        )
    return out
