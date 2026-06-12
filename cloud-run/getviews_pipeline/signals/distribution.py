from __future__ import annotations

import logging
import re
from typing import Any

from getviews_pipeline.corpus_boost_suspect import (
    boost_percentiles_from_niche_intel,
    classify_boost_suspect,
)
from getviews_pipeline.signals.base import Evidence, Signal
from getviews_pipeline.stats_history_m4 import compute_distribution_shape

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
                section_id="metadata",
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
                    section_id="metadata",
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
                section_id="metadata",
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


def extract_distribution_spike_then_flat_signal(ctx: dict) -> list[Signal]:
    us = _user_stats(ctx)
    history = ctx.get("stats_history") or us.get("stats_history")
    shape = ctx.get("distribution_shape") or us.get("distribution_shape")
    if shape != "spike_then_flat":
        shape = compute_distribution_shape(history)
    if shape != "spike_then_flat" or not isinstance(history, list):
        return []

    by_phase = {
        str(s.get("phase")): s
        for s in history
        if isinstance(s, dict) and s.get("phase")
    }
    t0 = by_phase.get("t0") or {}
    t6 = by_phase.get("t6h") or {}
    t24 = by_phase.get("t24h") or {}
    try:
        v0 = int(t0.get("views") or 0)
        v6 = int(t6.get("views") or 0)
        v24 = int(t24.get("views") or 0)
    except (TypeError, ValueError):
        return []

    return [
        Signal(
            id="distribution_spike_then_flat",
            section_id="boost_attribution",
            taxonomy_ref="§4.7 M4",
            salience=0.82,
            claim=(
                f"Có dấu hiệu đẩy view sớm ({v0:,}→{v6:,} trong ~6h) rồi tương tác không theo "
                f"tại ~24h ({v24:,} view) — pattern spike-then-flat, không khẳng định ads poisoning."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=(
                        f"t0_views={v0} t6h_views={v6} t24h_views={v24} "
                        f"t6h_at={t6.get('at')} t24h_at={t24.get('at')}"
                    ),
                    location="stats_history",
                )
            ],
            suggested_fix="Tách benchmark organic trước khi scale ads; theo dõi comment/ER sau boost.",
        )
    ]


def _boost_evidence_strength(
    *,
    attribution: str,
    views: int,
    er: float,
    comments: int,
    pct: Any,
) -> str:
    if attribution == "suspect_low":
        return "weak"
    if attribution != "suspect_medium":
        return "weak"
    p75 = max(float(pct.p75_views), 10_000.0)
    p10_er = float(pct.p25_er) * 0.4
    if comments == 0 and views >= max(10_000, p75):
        return "strong"
    if views >= float(pct.p90_views) and er < p10_er:
        return "strong"
    return "medium"


def extract_boost_tradeoff_education_signal(ctx: dict) -> list[Signal]:
    """P1 — lợi/hại ads khi evidence_strength ≥ medium."""
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
    strength = _boost_evidence_strength(
        attribution=result.attribution,
        views=views,
        er=er_f,
        comments=comments,
        pct=pct,
    )
    if strength not in ("medium", "strong"):
        return []

    return [
        Signal(
            id="boost_tradeoff_education",
            section_id="boost_attribution",
            taxonomy_ref="§4.7.0",
            salience=0.8 if strength == "strong" else 0.72,
            claim=(
                f"View ~{views:,} với ER {er_f:.1f}% — có dấu hiệu đẩy ads/seeding. "
                "Ads có thể mồi view nhanh nhưng làm lệch benchmark organic và "
                "poisoning tệp retarget nếu hook không giữ ER."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=(
                        f"views={views} er={er_f:.2f} evidence_strength={strength} "
                        f"attribution={result.attribution}"
                    ),
                    location="user_stats+niche_meta",
                )
            ],
            suggested_fix=(
                "Chạy thử organic trước; nếu boost, theo dõi comment/ER 24h và "
                "tách cohort benchmark."
            ),
        )
    ]


def _comment_radar(ctx: dict) -> dict:
    cr = ctx.get("comment_radar")
    return cr if isinstance(cr, dict) else {}


def _radar_neutral_pct(radar: dict) -> float:
    sentiment = radar.get("sentiment")
    if isinstance(sentiment, dict) and sentiment.get("neutral_pct") is not None:
        try:
            return float(sentiment["neutral_pct"])
        except (TypeError, ValueError):
            pass
    try:
        return float(radar.get("neutral_pct") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _fmt_comment_rate_per_1000(comment_rate: float) -> str:
    """Creator-readable comment density — ``0.26 comment/1.000 view``.

    Bug 2026-06-12: the raw ratio leaked into prose as «tỉ lệ 0.000258»,
    which is unreadable for creators.
    """
    return f"{comment_rate * 1000:.2f} comment/1.000 view"


def extract_seeding_comment_pattern_signal(ctx: dict) -> list[Signal]:
    """§4.7 M5 — comment spam/neutral skew + thin engagement on high views.

    Coherence guard (bug 2026-06-12): the report's boost chip renders
    ``meta.boost_attribution`` ("Organic — không thấy dấu hiệu boost" when
    ``organic_confident``). A seeding claim fired off a low comment ratio
    alone contradicted that chip in the same report — so this signal now
    requires boost suspicion (stored row attribution or the live
    classification), and is suppressed outright when the stored attribution
    says ``organic_confident``.
    """
    radar = _comment_radar(ctx)
    sampled = int(radar.get("sampled") or 0)
    if sampled < 8:
        return []

    try:
        spam_skipped_ratio = float(radar.get("spam_skipped_ratio") or 0.0)
    except (TypeError, ValueError):
        spam_skipped_ratio = 0.0
    neutral_pct = _radar_neutral_pct(radar)
    if spam_skipped_ratio < 0.5 and neutral_pct < 85.0:
        return []

    us = _user_stats(ctx)
    stored_attribution = str(us.get("boost_attribution") or "").strip().lower()
    if stored_attribution == "organic_confident":
        return []

    views = int(us.get("views") or 0)
    comments = int(us.get("comments") or 0)
    if views < 10_000:
        return []

    comment_rate = (comments / views) if views > 0 else 0.0
    er = us.get("engagement_rate")
    try:
        er_f = float(er or 0)
    except (TypeError, ValueError):
        er_f = 0.0
    if er_f <= 1.0:
        er_f *= 100.0

    pct = boost_percentiles_from_niche_intel(_niche_meta(ctx))
    boost = classify_boost_suspect(
        views=views,
        er=er_f,
        comments=comments,
        percentiles=pct,
        hard_reject_enabled=False,
    )
    boost_suspect = (
        boost.attribution in ("suspect_low", "suspect_medium")
        or stored_attribution in ("suspect_low", "suspect_medium")
    )
    if not boost_suspect:
        return []

    return [
        Signal(
            id="seeding_comment_pattern",
            section_id="boost_attribution",
            taxonomy_ref="§4.7 M5",
            salience=0.8,
            claim=(
                f"Có dấu hiệu seeding ảo: {sampled} comment mẫu, "
                f"{neutral_pct:.0f}% trung tính, spam skip {spam_skipped_ratio:.0%}; "
                f"{views:,} view với {comments} comment "
                f"({_fmt_comment_rate_per_1000(comment_rate)}) — "
                f"không khẳng định boost chắc."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=(
                        f"sampled={sampled} neutral_pct={neutral_pct:.1f} "
                        f"spam_skipped_ratio={spam_skipped_ratio:.2f} "
                        f"views={views} comments={comments}"
                    ),
                    location="comment_radar+user_stats",
                )
            ],
            suggested_fix="Đối chiếu hook/ER organic trước khi scale; kiểm tra comment thật.",
        )
    ]


def extract_live_boost_attribution_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_boost_views_er_mismatch_signal(ctx))
    out.extend(extract_boost_breakout_low_engagement_signal(ctx))
    out.extend(extract_distribution_spike_then_flat_signal(ctx))
    out.extend(extract_boost_tradeoff_education_signal(ctx))
    out.extend(extract_seeding_comment_pattern_signal(ctx))
    if out:
        logger.info(
            "[signals/distribution] boost_attribution fired ids=%s",
            [s.id for s in out],
        )
    return out
