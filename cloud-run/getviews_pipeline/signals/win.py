"""§4.8.3 Win path W0 signals — tier_gate=hit (salience only when performance_tier is hit)."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.enum_labels_vi import hook_type_vi
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
                f"Tỷ lệ tương tác {er_f:.1f}% ≥ ngưỡng cao của ngách (~{threshold:.1f}%) — "
                "lượt xem có chất lượng tương tác tốt so với các video cùng ngách."
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
                f"Hook «{hook_type_vi(ht, default=ht)}» ({ht}) trùng top hook đang tích lũy "
                f"view trong ngách ({', '.join(hook_type_vi(t, default=t) for t in top)}) — "
                "cơ chế mở bài khớp pattern thắng."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_type={ht} top={','.join(top)}",
                    location="user_analysis.hook_analysis+niche_meta.hook_distribution",
                )
            ],
            suggested_fix="Giữ nguyên công thức hook; thử nghiệm các biến thể khác cùng nhóm thay vì thay đổi hoàn toàn hình mẫu nội dung.",
        )
    ]


def extract_win_breakout_vs_channel_signal(ctx: dict) -> list[Signal]:
    if not _tier_gated(ctx):
        return []
    us = _user_stats(ctx)
    bm_raw = us.get("breakout_multiplier") or us.get("target_vs_creator_median")
    if bm_raw is None:
        return []
    try:
        bm = float(bm_raw)
    except (TypeError, ValueError):
        return []
    if bm < 2.0:
        return []

    med = us.get("creator_median_views")
    views = int(us.get("views") or 0)
    med_i = int(med) if med is not None else None
    base = (
        f"Video vượt trội ×{bm:.1f} so với mức view thường trên kênh ({med_i:,} lượt xem)"
        if med_i is not None
        else f"Video vượt trội ×{bm:.1f} so với mức thường ngày trên kênh"
    )
    claim = base + f" — {views:,} lượt xem cho thấy cơ chế mạnh hơn pattern thường."

    return [
        Signal(
            id="win_breakout_vs_channel",
            section_id="channel_pattern",
            taxonomy_ref="§4.8.3",
            salience=0.87,
            claim=claim,
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"breakout_multiplier={bm:.2f} views={views} creator_median={med_i}",
                    location="user_stats.breakout_multiplier",
                )
            ],
            suggested_fix="Nhân bản format/hook của hit này trong 2 video tiếp theo.",
        )
    ]


def extract_win_format_in_growth_signal(ctx: dict) -> list[Signal]:
    if not _tier_gated(ctx):
        return []
    nm = _niche_meta(ctx)
    dist = nm.get("format_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE:
        return []

    fmt = str(ctx.get("content_format") or "").strip().lower().replace("-", "_")
    if not fmt:
        return []

    items = sorted(
        ((str(k).strip().lower().replace("-", "_"), int(v)) for k, v in dist.items() if int(v or 0) > 0),
        key=lambda x: -x[1],
    )
    if len(items) < 2:
        return []
    top_share = items[0][1]
    fmt_share = next((share for name, share in items if name == fmt), 0)
    if fmt_share < top_share * 0.85:
        return []

    return [
        Signal(
            id="win_format_in_growth",
            section_id="niche_pattern",
            taxonomy_ref="§4.8.3",
            salience=0.85,
            claim=(
                f"Format `{fmt}` đang nằm nhóm tích lũy view trong ngách "
                f"({fmt_share}% corpus) — video khớp sóng growth."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"content_format={fmt} format_share={fmt_share}%",
                    location="content_format+niche_meta.format_distribution",
                )
            ],
            suggested_fix="Giữ format; thử biến thể hook trong cùng family.",
        )
    ]


def _verbal_cta_present(ctx: dict) -> bool:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    ci = ua.get("commerce_intent") or {}
    if isinstance(ci, dict) and ci.get("verbal_cta_present"):
        return True
    return bool(str(ua.get("cta") or "").strip())


def extract_win_replicable_cta_signal(ctx: dict) -> list[Signal]:
    if not _tier_gated(ctx):
        return []
    if not _verbal_cta_present(ctx):
        return []

    fmt = str(ctx.get("content_format") or "").strip()
    if not fmt or fmt.lower() in ("none", "other"):
        return []

    ua = ctx.get("user_analysis") or {}
    cta = str((ua.get("commerce_intent") or {}).get("verbal_cta_quote") or ua.get("cta") or "").strip()

    return [
        Signal(
            id="win_replicable_cta",
            section_id="commerce",
            taxonomy_ref="§4.8.3",
            salience=0.82,
            claim=(
                f"CTA lời nói rõ + format `{fmt}` lặp lại được — "
                "cơ chế chuyển đổi có thể nhân bản video sau."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"cta={cta[:80]} format={fmt}",
                    location="user_analysis.cta+content_format",
                )
            ],
            suggested_fix="Giữ CTA verbal + cấu trúc format; đổi hook line mỗi tuần.",
        )
    ]


def extract_win_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_win_er_above_niche_p75_signal(ctx))
    out.extend(extract_win_hook_aligns_niche_top_signal(ctx))
    out.extend(extract_win_breakout_vs_channel_signal(ctx))
    out.extend(extract_win_format_in_growth_signal(ctx))
    out.extend(extract_win_replicable_cta_signal(ctx))
    if out:
        logger.info(
            "[signals/win] fired ids=%s tier=%s",
            [s.id for s in out],
            ctx.get("performance_tier"),
        )
    return out
