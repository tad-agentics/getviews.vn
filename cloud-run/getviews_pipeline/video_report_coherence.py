"""Keep video diagnosis mode, structural errors, and follow-up copy aligned with performance_tier."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

VideoMode = Literal["win", "flop"]

# Channel-relative breakout — align with refine_performance_tier account_ratio >= 2.0
_CHANNEL_BREAKOUT_RATIO = 2.0


def _channel_breakout_from_meta(
    *,
    views: int,
    creator_median_views: int | float | None,
    target_vs_creator_median: float | None,
) -> bool:
    if target_vs_creator_median is not None and target_vs_creator_median >= _CHANNEL_BREAKOUT_RATIO:
        return True
    if creator_median_views is None:
        return False
    try:
        median = float(creator_median_views)
    except (TypeError, ValueError):
        return False
    if median <= 0 or views < 0:
        return False
    return float(views) / median >= _CHANNEL_BREAKOUT_RATIO


def tier_implies_win_framing(
    performance_tier: str | None,
    *,
    views: int = 0,
    creator_median_views: int | float | None = None,
    target_vs_creator_median: float | None = None,
) -> bool:
    """True when the video should not use flop framing (hit or channel breakout)."""
    tier = str(performance_tier or "unknown").lower()
    if tier == "hit":
        return True
    if tier == "flop":
        return False
    # average / unknown — still flip when channel evidence is strong
    return _channel_breakout_from_meta(
        views=views,
        creator_median_views=creator_median_views,
        target_vs_creator_median=target_vs_creator_median,
    )


def reconcile_video_mode(
    mode: str | None,
    performance_tier: str | None,
    *,
    views: int = 0,
    creator_median_views: int | float | None = None,
    target_vs_creator_median: float | None = None,
) -> VideoMode:
    """When tier/channel contradicts user-requested flop, trust measured performance."""
    m: VideoMode = "flop" if str(mode or "").lower() == "flop" else "win"
    if m == "flop" and tier_implies_win_framing(
        performance_tier,
        views=views,
        creator_median_views=creator_median_views,
        target_vs_creator_median=target_vs_creator_median,
    ):
        return "win"
    return m


def infer_early_performance_tier(
    views: int,
    corpus_avg_views: float | None,
    *,
    creator_median_views: int | float | None = None,
) -> str:
    """Corpus tier + channel median hint before async channel_context fetch."""
    from getviews_pipeline.pipelines import classify_performance_tier_corpus

    tier = classify_performance_tier_corpus(views, corpus_avg_views)
    if tier == "hit" or tier == "flop":
        return tier
    if _channel_breakout_from_meta(
        views=views,
        creator_median_views=creator_median_views,
        target_vs_creator_median=None,
    ):
        return "hit"
    return tier


def pipeline_reconcile_mode(
    mode_resolved: VideoMode,
    video: dict[str, Any],
    niche_intel: dict[str, Any] | None,
) -> VideoMode:
    """Single entry for corpus + on-demand pipelines before error extraction."""
    views = int(video.get("views") or 0)
    corpus_avg = float((niche_intel or {}).get("avg_views") or 0) or None
    cmv = video.get("creator_median_views")
    early_tier = infer_early_performance_tier(
        views,
        corpus_avg,
        creator_median_views=cmv,
    )
    reconciled = reconcile_video_mode(
        mode_resolved,
        early_tier,
        views=views,
        creator_median_views=cmv,
    )
    if reconciled != mode_resolved:
        logger.info(
            "[video_coherence] pipeline mode %s -> %s (early_tier=%s views=%s video_id=%s)",
            mode_resolved,
            reconciled,
            early_tier,
            views,
            video.get("video_id"),
        )
    return reconciled


def filter_structural_errors_for_tier(
    errors: list[dict[str, Any]] | None,
    performance_tier: str | None,
    *,
    views: int = 0,
    creator_median_views: int | float | None = None,
    target_vs_creator_median: float | None = None,
) -> list[dict[str, Any]]:
    """Drop modeled retention artifacts when win framing applies (hit or channel breakout)."""
    rows = [e for e in (errors or []) if isinstance(e, dict)]
    if not tier_implies_win_framing(
        performance_tier,
        views=views,
        creator_median_views=creator_median_views,
        target_vs_creator_median=target_vs_creator_median,
    ):
        return rows

    filtered: list[dict[str, Any]] = []
    dropped = 0
    for e in rows:
        eid = str(e.get("error_id") or "")
        detail = str(e.get("detail") or "")
        if eid == "ERR_retention_drop_3s":
            dropped += 1
            continue
        if "100%" in detail and any(k in detail.lower() for k in ("mất", "rời", "drop")):
            dropped += 1
            continue
        filtered.append(e)

    if dropped:
        logger.debug(
            "[video_coherence] filtered %d retention-artifact errors (win-framing views=%s)",
            dropped,
            views,
        )

    high = [e for e in filtered if str(e.get("sev") or "").lower() == "high"]
    if high:
        return high[:3]
    return filtered[:2]


def should_fill_related_questions(out: dict[str, Any]) -> bool:
    """Fill when BE never set the slot or returned an empty list (report_video default)."""
    rq = out.get("related_questions")
    return rq is None or (isinstance(rq, list) and len(rq) == 0)


def build_video_related_questions(
    *,
    performance_tier: str | None,
    mode: str | None,
    creator_handle: str | None,
    niche_label: str | None,
    content_format: str | None,
    views: int = 0,
    creator_median_views: int | float | None = None,
    target_vs_creator_median: float | None = None,
) -> list[str]:
    """Deterministic follow-ups for answer-session composer (≤120 chars each)."""
    win_framing = tier_implies_win_framing(
        performance_tier,
        views=views,
        creator_median_views=creator_median_views,
        target_vs_creator_median=target_vs_creator_median,
    ) or str(mode or "").lower() == "win"
    niche = (niche_label or "ngách của bạn").strip()[:40]
    handle = (creator_handle or "").strip().lstrip("@")
    fmt = (content_format or "format này").strip()[:32]

    if win_framing:
        qs = [
            f"Hook 3 giây đầu của @{handle or 'kênh'} cần tối ưu gì để giữ view cao hơn?",
            f"3 video {fmt} đang breakout trong {niche} — học gì từ frame đầu?",
            "Viết shot-list video tiếp theo giữ công thức đang thắng — hook + CTA cụ thể.",
        ]
    else:
        qs = [
            "Sửa hook 0–3s: mở bằng mặt + text overlay cụ thể cho video tiếp theo?",
            f"Format nào trong {niche} đang có view TB cao nhất tuần này?",
            f"So sánh video yếu với top 3 @{handle or 'đối thủ'} cùng ngách.",
        ]
    return [q.strip()[:120] for q in qs if q.strip()][:3]
