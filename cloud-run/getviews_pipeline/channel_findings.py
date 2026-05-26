"""Channel diagnosis findings layer (§5.3.3 P0) — evidence-backed memo inject."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from getviews_pipeline.channel_diagnose import classify_format, compute_posting_cadence
from getviews_pipeline.compliance import collect_compliance_flags

_ICT = ZoneInfo("Asia/Ho_Chi_Minh")

Strength = Literal["low", "medium", "high"]
PROMPT_FINDINGS_CAP = 8

_FORMAT_ENTROPY_HIGH = 2.2
_PEER_FORMAT_SATURATION_PCT = 70
_HANDLE_CORPUS_LOOKBACK_DAYS = 90
_HANDLE_CORPUS_SAMPLE_N = 15
_BOOST_OUTLIER_MIN_SAMPLE = 3
_BOOST_OUTLIER_MIN_COUNT = 2
_BOOST_OUTLIER_SHARE_PCT = 25
_SLANG_DATED_MIN_COUNT = 2
_PERSONA_DRIFT_MIN_CC_CHANGES = 2
_PERSONA_DRIFT_MIN_DRIFT_VIDEOS = 2
_PERSONA_CONSISTENCY_AXES = (
    "backdrop",
    "costume",
    "catchphrase",
    "camera_angle",
    "speech_register",
)
_CADENCE_PEER_LAG_PCT = 20
_BEST_HOUR_RATIO_MIN = 1.5
_BEST_HOUR_POST_SHARE_MAX = 0.35
_RESTRICTED_MIN_VIDEOS = 2
_DISCLOSURE_GAP_MIN_VIDEOS = 2
_CML_RISK_MIN_VIDEOS = 2
_MEGA_SALE_DIP_PCT = 40
# Static VN mega-sale anchors (month, day) ±2 days ICT — §5.3.3 P2
_MEGA_SALE_ANCHORS: tuple[tuple[int, int], ...] = (
    (3, 3),
    (6, 6),
    (8, 8),
    (9, 9),
    (10, 10),
    (11, 11),
    (12, 12),
)

POLICY_RISK_FINDING_IDS = frozenset({
    "channel_compliance_aggregate",
    "channel_restricted_keyword_exposure",
    "channel_ad_law_disclosure_gap",
    "channel_copyright_mute_risk",
})

ACCOUNT_HEALTH_FINDING_IDS = frozenset({
    "channel_view_ceiling_300",
    "channel_boost_outlier_share",
})


def format_distribution_from_corpus_rows(
    rows: list[dict[str, Any]] | None,
) -> dict[str, int]:
    """Share % by ``content_format`` from peer corpus rows (§5.3.5)."""
    if not rows:
        return {}
    counter: Counter[str] = Counter()
    for row in rows:
        fmt = str(row.get("content_format") or "").strip()
        if fmt:
            counter[fmt] += 1
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {fmt: round(100 * n / total) for fmt, n in counter.items()}


def _cohort_er_threshold_pct(niche_benchmarks: dict[str, Any] | None) -> float:
    """Low-ER bar for view-ceiling finding — p50×0.85 proxy when p25 absent."""
    default = 2.0
    if not niche_benchmarks:
        return default
    for key, scale in (("engagement_p25", 1.0), ("engagement_p50", 0.85)):
        raw = niche_benchmarks.get(key)
        if raw is None:
            continue
        try:
            v = float(raw) * scale
            return v * 100.0 if v <= 1.0 else v
        except (TypeError, ValueError):
            continue
    return default


@dataclass(frozen=True)
class ChannelFinding:
    id: str
    taxonomy_ref: str
    strength: Strength
    claim: str
    evidence: list[str]
    section_hint: str
    salience: float


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _video_er_pct(video: dict[str, Any]) -> float:
    views = int(video.get("views") or 0)
    if views <= 0:
        return 0.0
    likes = int(video.get("likes") or 0)
    comments = int(video.get("comments") or 0)
    return (likes + comments) / views * 100.0


def _shannon_entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _finding_view_ceiling_300(
    videos: list[dict[str, Any]],
    *,
    er_threshold_pct: float,
) -> ChannelFinding | None:
    cutoff = _now() - timedelta(days=90)
    low_ceiling: list[dict[str, Any]] = []
    for v in videos:
        posted = v.get("posted_at")
        if posted and isinstance(posted, datetime) and posted < cutoff:
            continue
        views = int(v.get("views") or 0)
        if views > 300:
            continue
        er = _video_er_pct(v)
        if er >= er_threshold_pct:
            continue
        low_ceiling.append(v)

    if len(low_ceiling) < 3:
        return None

    n = len(low_ceiling)
    return ChannelFinding(
        id="channel_view_ceiling_300",
        taxonomy_ref="§2.1",
        strength="high" if n >= 5 else "medium",
        claim=(
            f"{n} video gần đây kẹt dưới ~300 view với ER thấp — "
            "có dấu hiệu trần phân phối tài khoản; GetViews không đọc được FYP %."
        ),
        evidence=[
            f"low_view_low_er_count={n}/90d",
            f"er_threshold_pct={er_threshold_pct:.1f}",
        ],
        section_hint="verdict",
        salience=0.92 if n >= 5 else 0.85,
    )


def _finding_format_entropy_high(
    videos: list[dict[str, Any]],
    *,
    niche_format_distribution: dict[str, Any] | None,
) -> ChannelFinding | None:
    if len(videos) < 5:
        return None

    fmt_counts: dict[str, int] = {}
    for v in videos:
        fmt = str(v.get("content_format") or classify_format(v))
        fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1

    entropy = _shannon_entropy(fmt_counts)
    if entropy < _FORMAT_ENTROPY_HIGH:
        return None

    top_fmt, top_n = max(fmt_counts.items(), key=lambda kv: kv[1])
    top_share = round(100 * top_n / len(videos))

    niche_note = ""
    if isinstance(niche_format_distribution, dict) and niche_format_distribution:
        niche_top = max(niche_format_distribution.items(), key=lambda kv: int(kv[1] or 0))
        niche_note = f"niche_top_format={niche_top[0]}({niche_top[1]}%)"

    return ChannelFinding(
        id="channel_format_entropy_high",
        taxonomy_ref="§2.2",
        strength="medium",
        claim=(
            f"Format kênh phân tán (entropy={entropy:.2f}) — top chỉ {top_share}% "
            f"({top_fmt}); có dấu hiệu thiếu nhất quán ngách so với peer."
        ),
        evidence=[
            f"format_entropy={entropy:.2f}",
            f"top_format_share={top_share}%",
            niche_note or "niche_format_distribution=unavailable",
        ],
        section_hint="what_falling",
        salience=0.78,
    )


def _finding_recent_vs_peak_er_drop(
    videos: list[dict[str, Any]],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    channel_pattern: dict[str, Any],
) -> ChannelFinding | None:
    recent_count = int(recent_window_30d.get("video_count") or 0)
    if recent_count < 2:
        return None

    cutoff = _now() - timedelta(days=30)
    recent_vids = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    if not recent_vids:
        return None

    recent_er = sum(_video_er_pct(v) for v in recent_vids) / len(recent_vids)
    recent_avg = int(recent_window_30d.get("avg_views") or 0)

    peak_avg = int(channel_pattern.get("max_views") or 0)
    peak_er = recent_er
    if inflection:
        peak_avg = int(inflection.get("peak_avg") or peak_avg)
        peak_q = str(inflection.get("peak_quarter") or "")
        peak_start = inflection.get("peak_quarter_start")
        if peak_start and isinstance(peak_start, datetime):
            peak_vids = [
                v for v in videos
                if v.get("posted_at") and v["posted_at"] >= peak_start
            ]
            if peak_vids:
                peak_er = sum(_video_er_pct(v) for v in peak_vids) / len(peak_vids)
        elif peak_q:
            peak_vids = [v for v in videos if peak_q in str(v.get("posted_at") or "")]
            if peak_vids:
                peak_er = sum(_video_er_pct(v) for v in peak_vids) / len(peak_vids)

    if peak_avg <= 0 or recent_avg <= 0:
        return None

    view_drop_pct = (1.0 - recent_avg / peak_avg) * 100.0 if peak_avg > recent_avg else 0.0
    er_drop = peak_er - recent_er
    if view_drop_pct < 25.0 and er_drop < 1.0:
        return None

    return ChannelFinding(
        id="channel_recent_vs_peak_er_drop",
        taxonomy_ref="§2.2",
        strength="high" if view_drop_pct >= 40 else "medium",
        claim=(
            f"30 ngày gần: avg {recent_avg} view, ER ~{recent_er:.1f}% — "
            f"so đỉnh {peak_avg} view / ER ~{peak_er:.1f}%: có dấu hiệu lệch audience hoặc mất nhịp."
        ),
        evidence=[
            f"recent_30d_avg_views={recent_avg}",
            f"recent_er_pct={recent_er:.2f}",
            f"peak_avg_views={peak_avg}",
            f"peak_er_pct={peak_er:.2f}",
            f"view_drop_pct={view_drop_pct:.1f}",
        ],
        section_hint="what_falling",
        salience=0.88 if view_drop_pct >= 40 else 0.80,
    )


def _finding_peer_format_saturation(
    peer_corpus_rows: list[dict[str, Any]] | None,
    *,
    dominant_format: str | None,
) -> ChannelFinding | None:
    if not peer_corpus_rows or not dominant_format:
        return None

    fmt = str(dominant_format).strip()
    if not fmt:
        return None

    cutoff = _now() - timedelta(days=7)
    recent_peers: list[dict[str, Any]] = []
    for row in peer_corpus_rows[:20]:
        indexed = row.get("indexed_at")
        if indexed:
            if isinstance(indexed, str):
                try:
                    indexed_dt = datetime.fromisoformat(indexed.replace("Z", "+00:00"))
                except ValueError:
                    indexed_dt = None
            elif isinstance(indexed, datetime):
                indexed_dt = indexed if indexed.tzinfo else indexed.replace(tzinfo=UTC)
            else:
                indexed_dt = None
            if indexed_dt and indexed_dt < cutoff:
                continue
        recent_peers.append(row)

    pool = recent_peers if recent_peers else peer_corpus_rows[:20]
    if len(pool) < 5:
        return None

    same_fmt = sum(
        1 for r in pool
        if str(r.get("content_format") or "").strip() == fmt
    )
    share_pct = round(100 * same_fmt / len(pool))
    if share_pct < _PEER_FORMAT_SATURATION_PCT:
        return None

    return ChannelFinding(
        id="channel_peer_format_saturation",
        taxonomy_ref="§2.3",
        strength="medium",
        claim=(
            f"{share_pct}% video corpus top ngách 7d cùng format `{fmt}` — "
            "có dấu hiệu bão hòa format; cần góc lệch rõ so peer."
        ),
        evidence=[
            f"peer_format={fmt}",
            f"peer_same_format_share={share_pct}%",
            f"peer_sample_n={len(pool)}",
        ],
        section_hint="competitive_landscape",
        salience=0.76,
    )


def _parse_row_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _analysis_dict(row: dict[str, Any]) -> dict[str, Any]:
    aj = row.get("analysis_json")
    return aj if isinstance(aj, dict) else {}


def _filter_recent_handle_corpus_rows(
    rows: list[dict[str, Any]] | None,
    *,
    days: int = _HANDLE_CORPUS_LOOKBACK_DAYS,
    limit: int = _HANDLE_CORPUS_SAMPLE_N,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    cutoff = _now() - timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_row_ts(row.get("posted_at")) or _parse_row_ts(row.get("indexed_at"))
        if ts and ts < cutoff:
            continue
        recent.append(row)
        if len(recent) >= limit:
            break
    return recent if recent else list(rows[:limit])


def _row_has_disclosure_gap(aj: dict[str, Any]) -> bool:
    ci = aj.get("commerce_intent") if isinstance(aj.get("commerce_intent"), dict) else {}
    promo = str(aj.get("promotion_type") or "organic").lower()
    is_commercial = promo not in ("organic", "") or str(
        ci.get("conversion_objective") or "entertainment_first",
    ).lower() != "entertainment_first"
    if not is_commercial:
        return False
    if ci.get("disclosure_present"):
        return False
    if promo in ("brand_deal", "affiliate"):
        return True
    return bool(ci)


def _corpus_row_compliance_categories(row: dict[str, Any]) -> list[str]:
    aj = _analysis_dict(row)
    stats = {"caption": str(row.get("caption") or "")}
    cats: set[str] = set()
    for flag in collect_compliance_flags(aj, stats):
        cat = str(flag.get("category") or "restricted").strip()
        if cat:
            cats.add(cat)
    if _row_has_disclosure_gap(aj):
        cats.add("ad_law_disclosure")
    return sorted(cats)


def _persona_drift_axes(row: dict[str, Any]) -> list[str]:
    aj = _analysis_dict(row)
    pcs = aj.get("persona_consistency_signals")
    if not isinstance(pcs, dict):
        return []
    drifted: list[str] = []
    for axis in _PERSONA_CONSISTENCY_AXES:
        val = pcs.get(axis)
        if axis == "speech_register" and val is None:
            val = pcs.get("register")
        if str(val or "").strip().lower() == "drift":
            drifted.append(axis)
    return drifted


def _content_class_transitions(rows: list[dict[str, Any]]) -> int:
    ordered = sorted(
        rows,
        key=lambda r: _parse_row_ts(r.get("posted_at"))
        or _parse_row_ts(r.get("indexed_at"))
        or datetime.min.replace(tzinfo=UTC),
    )
    prev: int | None = None
    changes = 0
    for row in ordered:
        cc = row.get("content_class_id")
        if cc is None:
            continue
        cid = int(cc)
        if prev is not None and cid != prev:
            changes += 1
        prev = cid
    return changes


def _row_has_restricted_exposure(row: dict[str, Any]) -> bool:
    aj = _analysis_dict(row)
    stats = {"caption": str(row.get("caption") or "")}
    return bool(collect_compliance_flags(aj, stats))


def _row_is_commercial(aj: dict[str, Any], row: dict[str, Any]) -> bool:
    promo = str(aj.get("promotion_type") or row.get("promotion_type") or "organic").lower()
    if promo in ("brand_deal", "affiliate"):
        return True
    if row.get("is_commerce"):
        return True
    ci = aj.get("commerce_intent") if isinstance(aj.get("commerce_intent"), dict) else {}
    return str(ci.get("conversion_objective") or "entertainment_first").lower() != "entertainment_first"


def _row_has_cml_strip_risk(row: dict[str, Any]) -> bool:
    aj = _analysis_dict(row)
    if not _row_is_commercial(aj, row):
        return False
    tsp = aj.get("trending_sound_profile")
    if isinstance(tsp, dict) and tsp.get("commercial_music_library_eligible") is False:
        return True
    return False


def _in_mega_sale_window(dt: datetime, *, span_days: int = 2) -> bool:
    local = dt.astimezone(_ICT) if dt.tzinfo else dt.replace(tzinfo=UTC).astimezone(_ICT)
    for month, day in _MEGA_SALE_ANCHORS:
        try:
            anchor = datetime(local.year, month, day, tzinfo=_ICT)
        except ValueError:
            continue
        if abs((local.date() - anchor.date()).days) <= span_days:
            return True
    return False


def _avg_views_in_window(
    videos: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> float:
    vals: list[int] = []
    for v in videos:
        posted = v.get("posted_at")
        if not isinstance(posted, datetime):
            continue
        if start <= posted < end:
            vals.append(int(v.get("views") or 0))
    return sum(vals) / len(vals) if vals else 0.0


def _finding_channel_restricted_keyword_exposure(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if not pool:
        return None
    flagged = [r for r in pool if _row_has_restricted_exposure(r)]
    n = len(flagged)
    if n < _RESTRICTED_MIN_VIDEOS:
        return None
    share_pct = round(100 * n / len(pool))
    return ChannelFinding(
        id="channel_restricted_keyword_exposure",
        taxonomy_ref="§2.4",
        strength="high" if n >= 3 else "medium",
        claim=(
            f"{n}/{len(pool)} video corpus gần nhất có cụm từ/caption bị hạn chế "
            f"({share_pct}%) — rủi ro gỡ/tắt tiếng khi scale."
        ),
        evidence=[
            f"restricted_exposure_count={n}/{len(pool)}",
            f"restricted_share_pct={share_pct}",
        ],
        section_hint="policy_risk",
        salience=0.82 if n >= 3 else 0.76,
    )


def _finding_channel_ad_law_disclosure_gap(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    commercial = [r for r in pool if _row_is_commercial(_analysis_dict(r), r)]
    if not commercial:
        return None
    gaps = [r for r in commercial if _row_has_disclosure_gap(_analysis_dict(r))]
    n = len(gaps)
    if n < _DISCLOSURE_GAP_MIN_VIDEOS:
        return None
    share_pct = round(100 * n / len(commercial))
    return ChannelFinding(
        id="channel_ad_law_disclosure_gap",
        taxonomy_ref="§2.4",
        strength="high" if share_pct >= 50 else "medium",
        claim=(
            f"{n}/{len(commercial)} video thương mại thiếu disclosure (#qc/tiết lộ) "
            f"({share_pct}%) — cần bổ sung trước khi chạy brand/affiliate."
        ),
        evidence=[
            f"disclosure_gap_count={n}/{len(commercial)}",
            f"disclosure_gap_share_pct={share_pct}",
        ],
        section_hint="policy_risk",
        salience=0.81 if share_pct >= 50 else 0.75,
    )


def _finding_channel_copyright_mute_risk(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if not pool:
        return None
    at_risk = [r for r in pool if _row_has_cml_strip_risk(r)]
    n = len(at_risk)
    if n < _CML_RISK_MIN_VIDEOS:
        return None
    share_pct = round(100 * n / len(pool))
    return ChannelFinding(
        id="channel_copyright_mute_risk",
        taxonomy_ref="§2.4",
        strength="high" if n >= 3 else "medium",
        claim=(
            f"{n}/{len(pool)} video thương mại dùng sound không CML-safe "
            f"({share_pct}%) — rủi ro mute/strip khi đăng hoặc chạy ads."
        ),
        evidence=[
            f"cml_strip_risk_count={n}/{len(pool)}",
            f"cml_strip_share_pct={share_pct}",
        ],
        section_hint="policy_risk",
        salience=0.83 if n >= 3 else 0.78,
    )


def _finding_channel_posting_cadence_vs_peer(
    videos: list[dict[str, Any]],
    *,
    niche_benchmarks: dict[str, Any] | None,
) -> ChannelFinding | None:
    if len(videos) < 3:
        return None
    cadence = compute_posting_cadence(videos)
    ppw = float(cadence.get("posts_per_week") or 0)
    peer_median = float((niche_benchmarks or {}).get("posts_per_week_p50") or 0)
    if peer_median <= 0 or ppw <= 0:
        return None
    lag_pct = (peer_median - ppw) / peer_median * 100.0
    if lag_pct < _CADENCE_PEER_LAG_PCT:
        return None
    return ChannelFinding(
        id="channel_posting_cadence_vs_peer",
        taxonomy_ref="§1.5",
        strength="medium" if lag_pct < 35 else "high",
        claim=(
            f"Đăng {ppw:.1f} video/tuần — thấp hơn median ngách ({peer_median:.1f}) "
            f"khoảng {lag_pct:.0f}%; velocity thấp có thể làm giảm cold-start."
        ),
        evidence=[
            f"posts_per_week={ppw:.2f}",
            f"peer_median_posts_per_week={peer_median:.2f}",
            f"cadence_lag_pct={lag_pct:.1f}",
        ],
        section_hint="what_falling",
        salience=0.72 if lag_pct < 35 else 0.78,
    )


def _finding_channel_best_hour_underused(
    videos: list[dict[str, Any]],
) -> ChannelFinding | None:
    if len(videos) < 4:
        return None
    cadence = compute_posting_cadence(videos)
    ratio = float(cadence.get("best_hour_ratio") or 1.0)
    if ratio < _BEST_HOUR_RATIO_MIN:
        return None

    now = _now()
    cutoff = now - timedelta(days=30)
    recent = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    if len(recent) < 3:
        return None

    best_range = str(cadence.get("best_hour_range") or "")
    try:
        best_h = int(best_range.split("h")[0])
    except (ValueError, IndexError):
        return None
    end_h = min(best_h + 2, 23)
    in_best = sum(
        1 for v in recent
        if isinstance(v.get("posted_at"), datetime)
        and best_h <= v["posted_at"].hour <= end_h
    )
    share = in_best / len(recent)
    if share > _BEST_HOUR_POST_SHARE_MAX:
        return None

    share_pct = round(100 * share)
    return ChannelFinding(
        id="channel_best_hour_underused",
        taxonomy_ref="§1.5",
        strength="medium",
        claim=(
            f"Khung mạnh ~{best_range} cho view ~{ratio:.1f}x giờ yếu, "
            f"nhưng chỉ {share_pct}% video 30d đăng trong khung — đang bỏ lỡ cold-start."
        ),
        evidence=[
            f"best_hour_ratio={ratio:.2f}",
            f"best_hour_range={best_range}",
            f"posts_in_best_hour_share={share_pct}%",
        ],
        section_hint="recommendations",
        salience=0.70,
    )


def _finding_channel_mega_sale_dip(
    videos: list[dict[str, Any]],
) -> ChannelFinding | None:
    now = _now()
    if not _in_mega_sale_window(now):
        return None

    recent_start = now - timedelta(days=7)
    prior_start = now - timedelta(days=14)
    recent_avg = _avg_views_in_window(videos, recent_start, now)
    prior_avg = _avg_views_in_window(videos, prior_start, recent_start)
    if prior_avg <= 0 or recent_avg <= 0:
        return None

    dip_pct = (1.0 - recent_avg / prior_avg) * 100.0
    if dip_pct < _MEGA_SALE_DIP_PCT:
        return None

    return ChannelFinding(
        id="channel_mega_sale_dip",
        taxonomy_ref="§2.3",
        strength="high" if dip_pct >= 55 else "medium",
        claim=(
            f"Trong cửa sổ mega-sale ICT, view TB 7 ngày ~{int(recent_avg)} "
            f"giảm ~{dip_pct:.0f}% so 7 ngày trước (~{int(prior_avg)}) — "
            "có dấu hiệu audience chuyển sang deal/affiliate, ít xem organic."
        ),
        evidence=[
            f"recent_7d_avg_views={int(recent_avg)}",
            f"prior_7d_avg_views={int(prior_avg)}",
            f"view_dip_pct={dip_pct:.1f}",
            "mega_sale_window=active",
        ],
        section_hint="what_falling",
        salience=0.73 if dip_pct < 55 else 0.79,
    )


CHANNEL_MEMO_SECTION_ORDER: tuple[str, ...] = (
    "verdict",
    "what_worked",
    "what_falling",
    "video_vs_channel",
    "competitive_landscape",
    "hashtag_insights",
    "next_video",
    "account_health",
    "policy_risk",
    "recommendations",
)

_TRAJECTORY_SKIP_WHAT_FALLING = frozenset({"breakout", "new_account"})


def select_channel_sections_to_emit(
    findings: list[ChannelFinding],
    *,
    trajectory: str,
    video_url: str | None = None,
    has_next_video_seed: bool = False,
    has_ugc_peers: bool = False,
    peer_source: str | None = None,
) -> list[str]:
    """Salience-driven memo section list (§5.5 Wave 2 — channel analogue of V6 select)."""
    hints = {f.section_hint for f in findings}
    selected: set[str] = {"verdict", "what_worked", "recommendations", "hashtag_insights"}

    if trajectory not in _TRAJECTORY_SKIP_WHAT_FALLING:
        if not findings or "what_falling" in hints:
            selected.add("what_falling")

    if video_url:
        selected.add("video_vs_channel")

    if not findings:
        selected.add("competitive_landscape")
    elif has_ugc_peers or "competitive_landscape" in hints:
        selected.add("competitive_landscape")
    elif (peer_source or "") != "thin":
        selected.add("competitive_landscape")

    if has_next_video_seed:
        selected.add("next_video")

    selected.update(optional_memo_sections_from_findings(findings))

    return [sid for sid in CHANNEL_MEMO_SECTION_ORDER if sid in selected]


def optional_memo_sections_from_findings(
    findings: list[ChannelFinding],
) -> list[str]:
    """Layer B — optional SSE sections gated by finding salience (§5.3.2)."""
    ids = {f.id for f in findings}
    sections: list[str] = []
    if ids & POLICY_RISK_FINDING_IDS or any(
        f.section_hint == "policy_risk" for f in findings
    ):
        sections.append("policy_risk")
    if ids & ACCOUNT_HEALTH_FINDING_IDS or any(
        f.section_hint == "account_health" for f in findings
    ):
        sections.append("account_health")
    return sections


def synthesize_optional_section_from_findings(
    findings: list[ChannelFinding],
    section_id: str,
    *,
    trajectory: str = "stagnant",
) -> dict[str, str] | None:
    """Fallback memo block when LLM omits a gated optional section."""
    from getviews_pipeline.channel_diagnose_prompts import get_default_title

    if section_id == "account_health":
        relevant = [
            f for f in findings
            if f.id in ACCOUNT_HEALTH_FINDING_IDS or f.section_hint == section_id
        ]
    elif section_id == "policy_risk":
        relevant = [
            f for f in findings
            if f.id in POLICY_RISK_FINDING_IDS or f.section_hint == section_id
        ]
    else:
        relevant = [f for f in findings if f.section_hint == section_id]
    if not relevant:
        return None
    lines = [f.claim for f in relevant[:4]]
    return {
        "section_id": section_id,
        "title": get_default_title(section_id, trajectory),
        "text": "\n\n".join(lines),
    }


def _finding_channel_compliance_aggregate(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if not pool:
        return None

    flagged: list[tuple[str, list[str]]] = []
    for row in pool:
        cats = _corpus_row_compliance_categories(row)
        if cats:
            flagged.append((str(row.get("video_id") or ""), cats))

    if not flagged:
        return None

    n = len(flagged)
    total = len(pool)
    all_cats = sorted({c for _, cats in flagged for c in cats})
    strength: Strength = "high" if n >= 3 else "medium"

    return ChannelFinding(
        id="channel_compliance_aggregate",
        taxonomy_ref="§2.4",
        strength=strength,
        claim=(
            f"{n}/{total} video corpus gần nhất có dấu hiệu compliance "
            f"({', '.join(all_cats[:4])}) — nên rà soát caption/VO trước khi đăng tiếp."
        ),
        evidence=[
            f"flagged_videos={n}/{total}",
            f"compliance_categories={','.join(all_cats)}",
        ],
        section_hint="policy_risk",
        salience=0.86 if n >= 3 else 0.80,
    )


def _finding_channel_boost_outlier_share(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if len(pool) < _BOOST_OUTLIER_MIN_SAMPLE:
        return None

    suspect = [
        r for r in pool
        if str(r.get("boost_attribution") or "").strip() == "suspect_medium"
    ]
    n_suspect = len(suspect)
    if n_suspect < 1:
        return None

    share_pct = round(100 * n_suspect / len(pool))
    if n_suspect < _BOOST_OUTLIER_MIN_COUNT and share_pct < _BOOST_OUTLIER_SHARE_PCT:
        return None

    strength: Strength = "high" if share_pct >= 50 or n_suspect >= 3 else "medium"
    return ChannelFinding(
        id="channel_boost_outlier_share",
        taxonomy_ref="§1.8",
        strength=strength,
        claim=(
            f"{share_pct}% video corpus handle ({n_suspect}/{len(pool)}) "
            "có dấu hiệu view đẩy (suspect_medium) — benchmark organic có thể lệch."
        ),
        evidence=[
            f"suspect_medium_count={n_suspect}/{len(pool)}",
            f"suspect_medium_share={share_pct}%",
        ],
        section_hint="account_health",
        salience=0.84 if share_pct >= 50 else 0.77,
    )


def _finding_channel_persona_drift(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if len(pool) < 3:
        return None

    cc_changes = _content_class_transitions(pool)
    drift_videos = [r for r in pool if _persona_drift_axes(r)]
    n_drift = len(drift_videos)

    cc_ids = sorted({
        int(r["content_class_id"])
        for r in pool
        if r.get("content_class_id") is not None
    })

    cc_fires = cc_changes >= _PERSONA_DRIFT_MIN_CC_CHANGES
    pcs_fires = n_drift >= _PERSONA_DRIFT_MIN_DRIFT_VIDEOS
    if not cc_fires and not pcs_fires:
        return None

    parts: list[str] = []
    if cc_fires:
        parts.append(
            f"content_class đổi {cc_changes} lần trong 90d ({len(cc_ids)} class)"
        )
    if pcs_fires:
        parts.append(f"{n_drift} video có persona_consistency drift")

    strength: Strength = "high" if cc_fires and pcs_fires else "medium"
    return ChannelFinding(
        id="channel_persona_drift",
        taxonomy_ref="§2.5",
        strength=strength,
        claim=(
            "Kênh có dấu hiệu lệch persona/ngách — "
            + "; ".join(parts)
            + " — khán giả có thể không nhận ra 'mặt' kênh."
        ),
        evidence=[
            f"content_class_changes_90d={cc_changes}",
            f"distinct_content_class_ids={len(cc_ids)}",
            f"persona_drift_videos={n_drift}",
        ],
        section_hint="what_falling",
        salience=0.74 if cc_fires else 0.68,
    )


def _finding_channel_slang_staleness(
    handle_corpus_rows: list[dict[str, Any]] | None,
) -> ChannelFinding | None:
    pool = _filter_recent_handle_corpus_rows(handle_corpus_rows)
    if len(pool) < 3:
        return None

    dated_rows: list[dict[str, Any]] = []
    for row in pool:
        aj = _analysis_dict(row)
        tier = str(aj.get("slang_freshness_score") or "").strip().lower()
        if tier == "dated":
            dated_rows.append(row)

    n_dated = len(dated_rows)
    if n_dated < _SLANG_DATED_MIN_COUNT:
        return None

    share_pct = round(100 * n_dated / len(pool))
    strength: Strength = "medium" if share_pct < 50 else "high"
    return ChannelFinding(
        id="channel_slang_staleness",
        taxonomy_ref="§2.5",
        strength=strength,
        claim=(
            f"{n_dated}/{len(pool)} video corpus gần nhất dùng slang có dấu hiệu lỗi thời "
            f"({share_pct}%) — rủi ro không còn hợp Gen Z."
        ),
        evidence=[
            f"slang_dated_count={n_dated}/{len(pool)}",
            f"slang_dated_share={share_pct}%",
        ],
        section_hint="what_falling",
        salience=0.62 if share_pct < 50 else 0.70,
    )


def build_channel_findings(
    *,
    videos: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    niche_benchmarks: dict[str, Any] | None = None,
    peer_corpus_rows: list[dict[str, Any]] | None = None,
    handle_corpus_rows: list[dict[str, Any]] | None = None,
    dominant_format: str | None = None,
    niche_format_distribution: dict[str, Any] | None = None,
) -> list[ChannelFinding]:
    """Return channel findings sorted by salience desc (prompt caps at top 8)."""
    er_threshold = _cohort_er_threshold_pct(niche_benchmarks)

    candidates: list[ChannelFinding] = []
    for builder in (
        lambda: _finding_view_ceiling_300(videos, er_threshold_pct=er_threshold),
        lambda: _finding_format_entropy_high(
            videos, niche_format_distribution=niche_format_distribution,
        ),
        lambda: _finding_recent_vs_peak_er_drop(
            videos, recent_window_30d, inflection, channel_pattern,
        ),
        lambda: _finding_peer_format_saturation(
            peer_corpus_rows, dominant_format=dominant_format,
        ),
        lambda: _finding_channel_compliance_aggregate(handle_corpus_rows),
        lambda: _finding_channel_restricted_keyword_exposure(handle_corpus_rows),
        lambda: _finding_channel_ad_law_disclosure_gap(handle_corpus_rows),
        lambda: _finding_channel_copyright_mute_risk(handle_corpus_rows),
        lambda: _finding_channel_posting_cadence_vs_peer(
            videos, niche_benchmarks=niche_benchmarks,
        ),
        lambda: _finding_channel_best_hour_underused(videos),
        lambda: _finding_channel_boost_outlier_share(handle_corpus_rows),
        lambda: _finding_channel_mega_sale_dip(videos),
        lambda: _finding_channel_persona_drift(handle_corpus_rows),
        lambda: _finding_channel_slang_staleness(handle_corpus_rows),
    ):
        finding = builder()
        if finding:
            candidates.append(finding)

    candidates.sort(key=lambda f: -f.salience)
    return candidates


_QUICK_PEEK_FINDING_IDS = frozenset({
    "channel_view_ceiling_300",
    "channel_format_entropy_high",
})


def pick_channel_quick_peek(findings: list[ChannelFinding]) -> dict[str, str] | None:
    """F5 — return first P0 ceiling/entropy teaser for Trends card."""
    for finding in findings:
        if finding.id in _QUICK_PEEK_FINDING_IDS:
            return {"finding_id": finding.id, "teaser": finding.claim}
    return None


def serialize_findings_for_api(
    findings: list[ChannelFinding],
    *,
    limit: int = PROMPT_FINDINGS_CAP,
) -> list[dict[str, str]]:
    """API/SSE payload for deep channel findings tile (§5.1 gap 3)."""
    return [
        {
            "finding_id": f.id,
            "teaser": f.claim,
            "strength": f.strength,
            "section_hint": f.section_hint,
        }
        for f in findings[:limit]
    ]


def format_findings_for_prompt(findings: list[ChannelFinding]) -> str:
    """Render top findings for LLM context block."""
    if not findings:
        return ""
    lines = ["<<<CHANNEL FINDINGS>>>"]
    for f in findings[:PROMPT_FINDINGS_CAP]:
        ev = "; ".join(f.evidence)
        lines.append(
            f"- id={f.id} | strength={f.strength} | section_hint={f.section_hint} | "
            f"claim={f.claim} | evidence={ev}"
        )
    lines.append(
        "(Dùng findings làm bằng chứng số — KHÔNG khẳng định FYP % hay shadowban chắc chắn.)"
    )
    return "\n".join(lines)
