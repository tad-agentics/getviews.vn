"""§4.8.3 Win path W0 signals — tier_gate=hit (salience only when performance_tier is hit)."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

logger = logging.getLogger(__name__)

_MIN_NICHE_SAMPLE = 30
_HIT_TIER = "hit"


def _tier_gated(ctx: dict) -> bool:
    return str(ctx.get("performance_tier") or "").lower() == _HIT_TIER


def _niche_meta(ctx: dict) -> dict[str, Any]:
    nm = ctx.get("niche_meta")
    return nm if isinstance(nm, dict) else {}


def _user_stats(ctx: dict) -> dict[str, Any]:
    us = ctx.get("user_stats")
    return us if isinstance(us, dict) else {}


def _hook_analysis(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return {}
    ha = ua.get("hook_analysis") or {}
    return ha if isinstance(ha, dict) else {}


def _top_hook_types(dist: dict[str, Any], limit: int = 3) -> list[str]:
    items = sorted(
        (
            (str(k).strip().lower().replace("-", "_"), int(v))
            for k, v in dist.items()
            if int(v or 0) > 0
        ),
        key=lambda x: -x[1],
    )
    return [k for k, _ in items[:limit]]


def extract_win_er_above_niche_p75_signal(ctx: dict) -> list[Signal]:
    if not _tier_gated(ctx):
        return []
    nm = _niche_meta(ctx)
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    us = _user_stats(ctx)
    er = us.get("engagement_rate")
    if er is None:
        return []
    try:
        er_f = float(er)
    except (TypeError, ValueError):
        return []
    if er_f <= 1.0:
        er_f *= 100.0

    median_er = nm.get("median_er")
    if median_er is None:
        return []
    try:
        med = float(median_er)
    except (TypeError, ValueError):
        return []
    if med <= 1.0:
        med *= 100.0

    p75 = med * 1.15 if med > 0 else None
    threshold = p75 if p75 is not None else med
    if er_f < threshold:
        return []

    return [
        Signal(
            id="win_er_above_niche_p75",
            section_id="diagnosis",
            taxonomy_ref="§4.8.3",
            salience=0.88,
            claim=(
                f"Tỷ lệ tương tác {er_f:.1f}% ≥ ngưỡng p75 ngách (~{threshold:.1f}%) — "
                "view có chất lượng tương tác cao so với cohort."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"engagement_rate={er_f:.2f} threshold_p75≈{threshold:.2f}",
                    location="user_stats.engagement_rate+niche_meta.median_er",
                )
            ],
            suggested_fix="Giữ hook/CTA đang kéo ER; nhân bản format này trong 2–3 video tiếp.",
        )
    ]


def extract_win_hook_aligns_niche_top_signal(ctx: dict) -> list[Signal]:
    if not _tier_gated(ctx):
        return []
    nm = _niche_meta(ctx)
    dist = nm.get("hook_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    top = _top_hook_types(dist)
    if not top:
        return []

    ha = _hook_analysis(ctx)
    ht = str(ha.get("hook_type") or "").strip().lower().replace("-", "_")
    if not ht or ht in ("none", "other") or ht not in top:
        return []

    return [
        Signal(
            id="win_hook_aligns_niche_top",
            section_id="hook_analysis",
            taxonomy_ref="§4.8.3",
            salience=0.86,
            claim=(
                f"Hook `{ht}` trùng top hook đang tích lũy view trong ngách "
                f"({', '.join(top)}) — cơ chế mở bài khớp pattern thắng."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_type={ht} top={','.join(top)}",
                    location="user_analysis.hook_analysis+niche_meta.hook_distribution",
                )
            ],
            suggested_fix="Giữ công thức hook; thử biến thể cùng family (không đổi archetype).",
        )
    ]


def extract_win_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_win_er_above_niche_p75_signal(ctx))
    out.extend(extract_win_hook_aligns_niche_top_signal(ctx))
    if out:
        logger.info(
            "[signals/win] fired ids=%s tier=%s",
            [s.id for s in out],
            ctx.get("performance_tier"),
        )
    return out
