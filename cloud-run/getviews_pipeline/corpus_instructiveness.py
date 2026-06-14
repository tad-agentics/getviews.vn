"""Corpus ingest instructiveness scoring + purity selection (v1 criteria).

See ``artifacts/docs/corpus-ingest-criteria-v1.md``. Selection-only — does not
touch Gemini extraction (TD-7).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from getviews_pipeline.corpus_boost_suspect import (
    BoostPercentiles,
    BoostSuspectResult,
    boost_percentiles_from_niche_intel,
    classify_boost_suspect,
)
from getviews_pipeline.helpers import velocity_score
from getviews_pipeline.models import HookType
from getviews_pipeline.settings import settings

logger = logging.getLogger(__name__)

BreakoutSource = Literal[
    "author_median",
    "niche_p50",
    "class_p50",
    "niche_avg_fallback",
    "class_avg_fallback",
    "global_p50_fallback",
    "none",
]

_CJK_PATTERN = re.compile(r"[぀-ゟ゠-ヿ一-鿿가-힯]")

_CREATOR_TIER_MIN_VIEWS: dict[str, int] = {
    "nano": 3_000,
    "micro": 5_000,
    "mid": 15_000,
    "macro": 25_000,
    "mega": 80_000,
}

_HOOK_MARKERS: list[tuple[HookType, re.Pattern[str]]] = [
    ("question", re.compile(r"\?\s*$|tại sao|vì sao|ai biết", re.I)),
    ("bold_claim", re.compile(r"không ai|sự thật|thật ra|đừng tin", re.I)),
    ("curiosity_gap", re.compile(r"bí mật|không ngờ|ai ngờ|plot twist", re.I)),
    ("how_to", re.compile(r"cách |hướng dẫn|tutorial|mẹo |tip ", re.I)),
    ("story_open", re.compile(r"ngày |hôm đó|tui |mình từng|POV", re.I)),
    ("warning", re.compile(r"cảnh báo|đừng |tránh |sai lầm", re.I)),
    ("shock_stat", re.compile(r"\d+%|\d+ triệu|\d+k view", re.I)),
    ("comparison", re.compile(r"so sánh|vs |hơn |kém hơn", re.I)),
    ("social_proof", re.compile(r"review|đánh giá|mọi người|khách hàng", re.I)),
    ("pain_point", re.compile(r"mệt |stress|lo lắng|khó khăn", re.I)),
]


@dataclass
class NicheViewStats:
    niche_id: int
    p50_views: float = 0.0
    p75_views: float = 0.0
    p50_comment_rate: float = 0.0
    p50_save_rate: float = 0.0
    save_rate_row_count: int = 0
    corpus_count: int = 0
    organic_avg_views: float = 0.0


@dataclass
class ContentClassViewStats:
    content_class_id: int
    p50_views: float = 0.0
    p75_views: float = 0.0
    p50_comment_rate: float = 0.0
    p50_save_rate: float = 0.0
    save_rate_row_count: int = 0
    corpus_count: int = 0
    organic_avg_views: float = 0.0


@dataclass
class ContentClassTierViewStats:
    content_class_id: int
    creator_tier: str
    p50_views: float = 0.0
    corpus_count: int = 0


@dataclass
class GlobalViewStats:
    p50_views: float = 0.0
    p75_views: float = 0.0
    organic_avg_views: float = 0.0
    corpus_count: int = 0


@dataclass
class IngestBatchContext:
    """Prefetched stats for one batch night."""

    niche_stats: dict[int, NicheViewStats] = field(default_factory=dict)
    class_stats: dict[int, ContentClassViewStats] = field(default_factory=dict)
    class_tier_stats: dict[tuple[int, str], ContentClassTierViewStats] = field(default_factory=dict)
    global_stats: GlobalViewStats = field(default_factory=GlobalViewStats)
    global_boost: BoostPercentiles = field(default_factory=BoostPercentiles)
    niche_boost: dict[int, BoostPercentiles] = field(default_factory=dict)
    class_boost: dict[int, BoostPercentiles] = field(default_factory=dict)
    sound_momentum: dict[int, dict[str, str]] = field(default_factory=dict)
    author_median_cache: dict[str, int | None] = field(default_factory=dict)
    missing_median_count: int = 0
    missing_median_total: int = 0


@dataclass
class CandidateScore:
    aweme: dict[str, Any]
    instructiveness_score: float
    breakout_value: float
    breakout_source: BreakoutSource
    velocity: float
    boost: BoostSuspectResult
    predicted_hook: str | None
    hook_penalty_applied: bool
    would_skip_pre_gemini: bool
    tier1_pass: bool
    convergence_pass: bool
    relaxation_tier: int = 0


def corpus_ingest_mode() -> str:
    mode = (settings.corpus_ingest_mode or "legacy").strip().lower()
    if mode not in ("legacy", "shadow", "purity"):
        return "legacy"
    return mode


def corpus_score_cohort() -> str:
    """legacy | class_shadow | class — class_shadow scores on class, persists legacy."""
    mode = (settings.corpus_score_cohort or "legacy").strip().lower()
    if mode not in ("legacy", "class_shadow", "class"):
        return "legacy"
    return mode


def use_class_score_cohort() -> bool:
    return corpus_score_cohort() in ("class_shadow", "class")


def predict_content_class_pre_score(
    aweme: dict[str, Any],
    *,
    loop_niche_id: int,
) -> int | None:
    """Heuristic pre-score class from loop niche + content type (Phase 2 hook)."""
    from getviews_pipeline import ensemble
    from getviews_pipeline.corpus_ingest import _content_class_for

    ctype = ensemble.detect_content_type(aweme)
    fmt = "carousel" if ctype == "carousel" else "talking_head"
    return _content_class_for(loop_niche_id, fmt)


def pre_pool_min_views(mode: str | None = None) -> int:
    """Pre-pool view floor before Tier 1 instructiveness scoring.

    Legacy keeps flat ``batch_min_views`` (default 20k). Shadow/purity use the
    lowest tiered floor (nano 3k) so breakout peers are not dropped before
    ``_tier1_pass`` applies creator-tier min views + breakout/velocity gates.
    """
    m = mode if mode is not None else corpus_ingest_mode()
    if m in ("shadow", "purity"):
        return min(_CREATOR_TIER_MIN_VIEWS.values())
    return settings.batch_min_views


def effective_videos_per_niche(base_vpn: int) -> int:
    if corpus_ingest_mode() == "purity":
        return max(1, settings.corpus_purity_vpn_default)
    return base_vpn


def looks_like_non_vietnamese_caption(caption: str | None, threshold: float = 0.25) -> bool:
    if not caption:
        return False
    stripped = re.sub(r"\s+", "", caption)
    if not stripped:
        return False
    cjk = len(_CJK_PATTERN.findall(stripped))
    return (cjk / len(stripped)) > threshold


def predict_hook_from_caption(caption: str | None) -> str | None:
    if not caption:
        return None
    for hook_type, pattern in _HOOK_MARKERS:
        if pattern.search(caption):
            return hook_type
    return None


def _norm(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return min(max(value, 0.0) / cap, 1.0)


def _recency_bonus(create_time: int | None, *, now: float | None = None) -> float:
    if not create_time:
        return 0.0
    t = now if now is not None else time.time()
    age_days = max((t - create_time) / 86400.0, 0.0)
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.5
    if age_days <= 30:
        return 0.2
    return 0.0


def _author_median(aweme: dict[str, Any], ctx: IngestBatchContext) -> tuple[int | None, BreakoutSource]:
    author = aweme.get("author") or {}
    handle = str(author.get("unique_id") or "").lower().strip()
    if handle and handle in ctx.author_median_cache:
        med = ctx.author_median_cache[handle]
        return med, "author_median" if med else "none"

    author_stats = (
        aweme.get("authorStats")
        or aweme.get("author_stats")
        or author.get("authorStats")
        or author.get("author_stats")
        or {}
    )
    med_raw = author_stats.get("medianPlayCount") or author_stats.get("median_play_count")
    try:
        med = int(med_raw) if med_raw is not None else None
    except (TypeError, ValueError):
        med = None
    if handle:
        ctx.author_median_cache[handle] = med
    ctx.missing_median_total += 1
    if not med or med <= 0:
        ctx.missing_median_count += 1
        return None, "none"
    return med, "author_median"


def _stats_for_cohort(
    niche_id: int,
    content_class_id: int | None,
    ctx: IngestBatchContext,
) -> tuple[NicheViewStats | ContentClassViewStats | None, bool]:
    """Return (stats, used_class_axis)."""
    if use_class_score_cohort() and content_class_id is not None:
        cs = ctx.class_stats.get(content_class_id)
        if cs and cs.p50_views > 0:
            return cs, True
    return ctx.niche_stats.get(niche_id), False


def _breakout_for_aweme(
    aweme: dict[str, Any],
    views: int,
    niche_id: int,
    ctx: IngestBatchContext,
    *,
    content_class_id: int | None = None,
) -> tuple[float, BreakoutSource]:
    med, src = _author_median(aweme, ctx)
    if med and med > 0:
        return round(views / float(med), 2), "author_median"
    ns, used_class = _stats_for_cohort(niche_id, content_class_id, ctx)
    if ns and ns.p50_views > 0:
        src: BreakoutSource = "class_p50" if used_class else "niche_p50"
        return round(views / ns.p50_views, 2), src
    if ns and ns.organic_avg_views > 0 and ns.corpus_count >= 20:
        avg_src: BreakoutSource = "class_avg_fallback" if used_class else "niche_avg_fallback"
        return round(views / ns.organic_avg_views, 2), avg_src
    gs = ctx.global_stats
    if gs.p50_views > 0:
        return round(views / max(gs.p50_views, 1.0), 2), "global_p50_fallback"
    return 0.0, "none"


def sound_momentum_bonus(
    aweme: dict[str, Any],
    niche_id: int,
    ctx: IngestBatchContext,
) -> float:
    music = aweme.get("music") or {}
    sound_id = str(music.get("id") or music.get("mid") or "")
    bucket_map = ctx.sound_momentum.get(niche_id) or {}
    bucket = bucket_map.get(sound_id, "")
    bonus = 0.0
    if bucket == "accelerating":
        bonus = 6.0
    elif bucket == "peaking":
        bonus = 3.0
    title = str(music.get("title") or "").lower()
    is_original = bool(
        music.get("is_original")
        or music.get("is_original_sound")
        or title.startswith("original sound")
        or title.startswith("âm thanh gốc")
    )
    if is_original and settings.corpus_sound_organic_bonus > 0:
        bonus = min(6.0, bonus + settings.corpus_sound_organic_bonus)
    return bonus


def _tiered_min_views(creator_tier: str | None, relaxation_tier: int) -> int:
    tier = creator_tier or "micro"
    base = _CREATOR_TIER_MIN_VIEWS.get(tier, 5_000)
    if relaxation_tier >= 2:
        pct = settings.corpus_relax_view_floor_pct
        relaxed = int(base * (1.0 - pct))
        floor = 3_000 if tier == "nano" else 5_000
        return max(relaxed, floor)
    return base


def _classify_creator_tier(followers: int | None) -> str | None:
    if followers is None or followers < 0:
        return None
    if followers < 1_000:
        return "nano"
    if followers < 10_000:
        return "micro"
    if followers < 100_000:
        return "mid"
    if followers < 1_000_000:
        return "macro"
    return "mega"


def compute_instructiveness_score(
    aweme: dict[str, Any],
    *,
    niche_id: int,
    signal_hashtags: list[str],
    er: float,
    views: int,
    comments: int,
    save_rate: float | None,
    ctx: IngestBatchContext,
    relaxation_tier: int = 0,
    hook_type_counts: dict[str, int] | None = None,
    content_class_id: int | None = None,
) -> CandidateScore:
    hook_type_counts = hook_type_counts or {}
    score_cc = content_class_id
    if score_cc is None and use_class_score_cohort():
        score_cc = aweme.get("_ingest_loop_content_class_id")
        if score_cc is not None:
            try:
                score_cc = int(score_cc)
            except (TypeError, ValueError):
                score_cc = None
    breakout, breakout_source = _breakout_for_aweme(
        aweme, views, niche_id, ctx, content_class_id=score_cc,
    )
    vel = velocity_score(aweme)
    missing_median = breakout_source != "author_median"
    vel_weight = 25.0 if missing_median else 15.0

    ns, _ = _stats_for_cohort(niche_id, score_cc, ctx)
    comment_rate = (comments / views) if views > 0 else 0.0
    save_norm = 0.0
    comment_norm = 0.0
    if ns:
        if ns.p50_comment_rate > 0:
            comment_norm = _norm(comment_rate, ns.p50_comment_rate * 2)
        if save_rate is not None and ns.p50_save_rate > 0:
            save_norm = _norm(save_rate, ns.p50_save_rate * 2)

    hashtag_bonus = 0.0
    desc = str(aweme.get("desc") or "").lower()
    for tag in signal_hashtags:
        frag = tag.strip().lstrip("#").lower()
        if frag and frag in desc:
            hashtag_bonus = 5.0
            break

    create_time = aweme.get("createTime") or aweme.get("create_time")
    try:
        ct = int(create_time) if create_time is not None else None
    except (TypeError, ValueError):
        ct = None

    score = (
        25.0 * _norm(breakout, 10.0)
        + vel_weight * _norm(vel, 1.0)
        + 15.0 * save_norm
        + 12.0 * comment_norm
        + 12.0 * _norm(er, 10.0)
        + 10.0 * _recency_bonus(ct)
        + sound_momentum_bonus(aweme, niche_id, ctx)
        + hashtag_bonus
    )

    predicted = predict_hook_from_caption(str(aweme.get("desc") or ""))
    hook_penalty = False
    would_skip = False
    if predicted:
        count = hook_type_counts.get(predicted, 0)
        if count >= 5 and breakout < settings.corpus_hook_cap_breakout_bypass:
            would_skip = True
        elif count >= 3 and breakout < settings.corpus_hook_cap_breakout_bypass:
            score -= settings.corpus_hook_predict_penalty
            hook_penalty = True

    if use_class_score_cohort() and score_cc is not None:
        pct = ctx.class_boost.get(score_cc) or ctx.niche_boost.get(niche_id) or ctx.global_boost
    else:
        pct = ctx.niche_boost.get(niche_id) or ctx.global_boost
    boost = classify_boost_suspect(
        views=views,
        er=er,
        comments=comments,
        percentiles=pct,
        hard_reject_enabled=settings.corpus_boost_hard_reject,
    )

    tier1 = _tier1_pass(
        aweme,
        views=views,
        er=er,
        breakout=breakout,
        velocity=vel,
        ctx=ctx,
        relaxation_tier=relaxation_tier,
    )
    conv = _convergence_pass(
        aweme,
        niche_id=niche_id,
        views=views,
        comments=comments,
        comment_rate=comment_rate,
        save_rate=save_rate,
        er=er,
        breakout=breakout,
        velocity=vel,
        boost=boost,
        ctx=ctx,
        signal_hashtags=signal_hashtags,
        relaxation_tier=relaxation_tier,
        content_class_id=score_cc,
    )

    return CandidateScore(
        aweme=aweme,
        instructiveness_score=round(score, 2),
        breakout_value=breakout,
        breakout_source=breakout_source,
        velocity=vel,
        boost=boost,
        predicted_hook=predicted,
        hook_penalty_applied=hook_penalty,
        would_skip_pre_gemini=would_skip,
        tier1_pass=tier1,
        convergence_pass=conv,
        relaxation_tier=relaxation_tier,
    )


def _tier1_pass(
    aweme: dict[str, Any],
    *,
    views: int,
    er: float,
    breakout: float,
    velocity: float,
    ctx: IngestBatchContext,
    relaxation_tier: int,
) -> bool:
    author = aweme.get("author") or {}
    followers = author.get("follower_count") or author.get("followerCount")
    try:
        fl = int(followers) if followers is not None else None
    except (TypeError, ValueError):
        fl = None
    tier = _classify_creator_tier(fl)
    if views < _tiered_min_views(tier, relaxation_tier):
        return False

    if (
        settings.corpus_ingest_max_age_days > 0
        and relaxation_tier < 1
    ):
        ct = aweme.get("createTime") or aweme.get("create_time")
        try:
            ts = int(ct) if ct is not None else 0
        except (TypeError, ValueError):
            ts = 0
        if ts > 0:
            age_days = (time.time() - ts) / 86400.0
            if age_days > settings.corpus_ingest_max_age_days:
                return False

    instructiveness_or = (
        breakout >= 2.0
        or velocity >= settings.corpus_velocity_gate_min
        or (views >= settings.reference_ingest_min_views and er >= 3.0)
    )
    return instructiveness_or


def _convergence_pass(
    aweme: dict[str, Any],
    *,
    niche_id: int,
    views: int,
    comments: int,
    comment_rate: float,
    save_rate: float | None,
    er: float,
    breakout: float,
    velocity: float,
    boost: BoostSuspectResult,
    ctx: IngestBatchContext,
    signal_hashtags: list[str],
    relaxation_tier: int,
    content_class_id: int | None = None,
) -> bool:
    min_gates = (
        settings.corpus_convergence_relaxed_min_gates
        if relaxation_tier >= 1
        else settings.corpus_convergence_min_gates
    )
    gates = 0
    if breakout >= 2.0 or velocity >= settings.corpus_velocity_gate_min:
        gates += 1
    ns, _ = _stats_for_cohort(niche_id, content_class_id, ctx)
    if ns and ns.p50_comment_rate > 0 and comment_rate >= ns.p50_comment_rate:
        gates += 1
    elif save_rate is not None and save_rate > 0:
        gates += 1
    if sound_momentum_bonus(aweme, niche_id, ctx) > 0 or any(
        t.strip().lstrip("#").lower() in str(aweme.get("desc") or "").lower()
        for t in signal_hashtags
    ):
        gates += 1
    if not boost.would_reject:
        gates += 1
    return gates >= min_gates


def apply_diversity_caps(
    scored: list[CandidateScore],
    k: int,
    *,
    max_per_creator: int,
    max_per_sound: int,
) -> list[dict[str, Any]]:
    """Return aweme dicts after creator/sound caps."""
    creator_counts: dict[str, int] = {}
    sound_counts: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for item in scored:
        if item.would_skip_pre_gemini:
            continue
        aweme = item.aweme
        author = str((aweme.get("author") or {}).get("unique_id") or "").lower()
        music = aweme.get("music") or {}
        sound_id = str(music.get("id") or music.get("mid") or "")
        if author and creator_counts.get(author, 0) >= max_per_creator:
            continue
        if sound_id and sound_counts.get(sound_id, 0) >= max_per_sound:
            continue
        out.append(aweme)
        if author:
            creator_counts[author] = creator_counts.get(author, 0) + 1
        if sound_id:
            sound_counts[sound_id] = sound_counts.get(sound_id, 0) + 1
        if len(out) >= k:
            break
    return out


def select_purity_candidates(
    pool: list[dict[str, Any]],
    *,
    niche_id: int,
    signal_hashtags: list[str],
    k: int,
    ctx: IngestBatchContext,
    er_fn: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score, relax if needed, rank, cap — returns candidates + shadow log dict."""
    meta: dict[str, Any] = {"niche_id": niche_id}

    def _score_batch(relax: int) -> list[CandidateScore]:
        hook_counts: dict[str, int] = {}
        batch_scored: list[CandidateScore] = []
        for aweme in pool:
            stats = aweme.get("statistics") or {}
            views = int(stats.get("play_count") or stats.get("playCount") or 0)
            if views <= 0:
                continue
            likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
            comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
            shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
            er = er_fn(
                er_from_analysis=None,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
            )
            pre_cc = aweme.get("_ingest_loop_content_class_id")
            try:
                pre_cc_i = int(pre_cc) if pre_cc is not None else None
            except (TypeError, ValueError):
                pre_cc_i = None
            if pre_cc_i is None and use_class_score_cohort():
                pre_cc_i = predict_content_class_pre_score(aweme, loop_niche_id=niche_id)
                if pre_cc_i is not None:
                    aweme["_ingest_loop_content_class_id"] = pre_cc_i
            cs = compute_instructiveness_score(
                aweme,
                niche_id=niche_id,
                signal_hashtags=signal_hashtags,
                er=er,
                views=views,
                comments=comments,
                save_rate=None,
                ctx=ctx,
                relaxation_tier=relax,
                hook_type_counts=hook_counts,
                content_class_id=pre_cc_i,
            )
            if cs.predicted_hook:
                hook_counts[cs.predicted_hook] = hook_counts.get(cs.predicted_hook, 0) + 1
            batch_scored.append(cs)
        return batch_scored

    relaxation_tier = 0
    scored: list[CandidateScore] = []

    for relax in (0, 1, 2):
        scored = _score_batch(relax)
        tier1_pass = [s for s in scored if s.tier1_pass and s.convergence_pass]
        relaxation_tier = relax
        if len(tier1_pass) > settings.corpus_relax_trigger_max:
            break

    passing = [s for s in scored if s.tier1_pass and s.convergence_pass]
    if len(passing) < settings.corpus_tier1_min_extract_floor and scored:
        passing = sorted(scored, key=lambda s: s.instructiveness_score, reverse=True)[
            : settings.corpus_tier1_min_extract_floor
        ]
        relaxation_tier = max(relaxation_tier, 2)

    passing.sort(key=lambda s: s.instructiveness_score, reverse=True)
    selected = apply_diversity_caps(
        passing,
        k,
        max_per_creator=settings.corpus_max_per_creator,
        max_per_sound=settings.corpus_max_per_sound,
    )

    meta.update(
        {
            "relaxation_tier": relaxation_tier,
            "pool_size": len(pool),
            "tier1_pass_count": len([s for s in scored if s.tier1_pass]),
            "selected_count": len(selected),
            "top_scores": [s.instructiveness_score for s in passing[:10]],
        }
    )
    if settings.corpus_ingest_shadow_log:
        _log_shadow(niche_id, passing[:10], legacy_ids=[])
    return selected, meta


def _log_shadow(
    niche_id: int,
    top: list[CandidateScore],
    *,
    legacy_ids: list[str],
) -> None:
    payload = {
        "niche_id": niche_id,
        "top10": [
            {
                "aweme_id": str(s.aweme.get("aweme_id") or ""),
                "score": s.instructiveness_score,
                "breakout": s.breakout_value,
                "breakout_source": s.breakout_source,
                "boost": s.boost.attribution,
                "would_reject_boost": s.boost.would_reject,
                "predicted_hook": s.predicted_hook,
            }
            for s in top
        ],
        "legacy_top_ids": legacy_ids[:10],
    }
    logger.info("[corpus_shadow] %s", json.dumps(payload, ensure_ascii=False))


def prefetch_ingest_batch_context(client: Any, niche_ids: list[int]) -> IngestBatchContext:
    """Load niche p50/p75, boost percentiles, sound momentum for batch night."""
    from getviews_pipeline.corpus_windows import corpus_benchmark_window_days

    ctx = IngestBatchContext()
    since = (datetime.now(UTC) - timedelta(days=corpus_benchmark_window_days())).isoformat()
    select_cols = (
        "ingest_loop_niche_id, content_class_id, creator_tier, views, comments, save_rate, engagement_rate"
    )
    try:
        rows = (
            client.table("video_corpus")
            .select(select_cols)
            .gte("indexed_at", since)
            .eq("language", "vi")
            .limit(50_000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[corpus] prefetch video_corpus stats failed: %s", exc)
        rows = []

    by_niche: dict[int, list[dict[str, Any]]] = {}
    by_class: dict[int, list[dict[str, Any]]] = {}
    by_class_tier: dict[tuple[int, str], list[dict[str, Any]]] = {}
    all_views: list[float] = []
    all_comment_rates: list[float] = []
    all_er: list[float] = []
    for row in rows:
        nid = row.get("ingest_loop_niche_id")
        if nid is None:
            continue
        nid = int(nid)
        by_niche.setdefault(nid, []).append(row)
        cc = row.get("content_class_id")
        if cc is not None:
            cc_id = int(cc)
            by_class.setdefault(cc_id, []).append(row)
            tier = row.get("creator_tier")
            if tier:
                by_class_tier.setdefault((cc_id, str(tier)), []).append(row)
        v = float(row.get("views") or 0)
        if v > 0:
            all_views.append(v)
            c = float(row.get("comments") or 0)
            all_comment_rates.append(c / v)
            all_er.append(float(row.get("engagement_rate") or 0))

    def _pct(vals: list[float], p: float) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        idx = int((len(s) - 1) * p)
        return s[idx]

    ctx.global_boost = BoostPercentiles(
        sample_size=len(rows),
        p10_comment_rate=_pct(all_comment_rates, 0.10) or 0.001,
        p25_er=_pct(all_er, 0.25) or 2.0,
        p75_views=_pct(all_views, 0.75) or 10_000.0,
        p90_views=_pct(all_views, 0.90) or 50_000.0,
        thin=len(rows) < 50 * max(1, len(niche_ids)),
    )
    ctx.global_stats = GlobalViewStats(
        p50_views=_pct(all_views, 0.50),
        p75_views=_pct(all_views, 0.75),
        organic_avg_views=sum(all_views) / len(all_views) if all_views else 0.0,
        corpus_count=len(rows),
    )

    for nid, nrows in by_niche.items():
        views = [float(r.get("views") or 0) for r in nrows if float(r.get("views") or 0) > 0]
        comment_rates = []
        save_rates = []
        save_count = 0
        for r in nrows:
            v = float(r.get("views") or 0)
            if v > 0:
                comment_rates.append(float(r.get("comments") or 0) / v)
            sr = r.get("save_rate")
            if sr is not None:
                save_count += 1
                save_rates.append(float(sr))
        avg_views = sum(views) / len(views) if views else 0.0
        ctx.niche_stats[nid] = NicheViewStats(
            niche_id=nid,
            p50_views=_pct(views, 0.50),
            p75_views=_pct(views, 0.75),
            p50_comment_rate=_pct(comment_rates, 0.50),
            p50_save_rate=_pct(save_rates, 0.50),
            save_rate_row_count=save_count,
            corpus_count=len(nrows),
            organic_avg_views=avg_views,
        )

    for nid in niche_ids:
        try:
            ni = (
                client.table("niche_intelligence")
                .select("*")
                .eq("ingest_loop_niche_id", nid)
                .maybe_single()
                .execute()
                .data
            )
        except Exception:
            ni = None
        pct = boost_percentiles_from_niche_intel(ni)
        if pct.thin:
            pct = ctx.global_boost
        ns = ctx.niche_stats.get(nid)
        if ns and ns.p75_views > 0:
            pct = BoostPercentiles(
                sample_size=pct.sample_size,
                p10_comment_rate=pct.p10_comment_rate,
                p25_er=pct.p25_er,
                p75_views=ns.p75_views,
                p90_views=max(ns.p75_views * 1.5, pct.p90_views),
                thin=pct.thin,
            )
        ctx.niche_boost[nid] = pct

    for cc_id, crows in by_class.items():
        views = [float(r.get("views") or 0) for r in crows if float(r.get("views") or 0) > 0]
        comment_rates = []
        save_rates = []
        save_count = 0
        for r in crows:
            v = float(r.get("views") or 0)
            if v > 0:
                comment_rates.append(float(r.get("comments") or 0) / v)
            sr = r.get("save_rate")
            if sr is not None:
                save_count += 1
                save_rates.append(float(sr))
        avg_views = sum(views) / len(views) if views else 0.0
        ctx.class_stats[cc_id] = ContentClassViewStats(
            content_class_id=cc_id,
            p50_views=_pct(views, 0.50),
            p75_views=_pct(views, 0.75),
            p50_comment_rate=_pct(comment_rates, 0.50),
            p50_save_rate=_pct(save_rates, 0.50),
            save_rate_row_count=save_count,
            corpus_count=len(crows),
            organic_avg_views=avg_views,
        )
        cs = ctx.class_stats[cc_id]
        pct = BoostPercentiles(
            sample_size=len(crows),
            p10_comment_rate=ctx.global_boost.p10_comment_rate,
            p25_er=ctx.global_boost.p25_er,
            p75_views=cs.p75_views or ctx.global_boost.p75_views,
            p90_views=max(cs.p75_views * 1.5, ctx.global_boost.p90_views),
            thin=len(crows) < 15,
        )
        if pct.thin:
            pct = ctx.global_boost
        ctx.class_boost[cc_id] = pct

    for (cc_id, tier), trows in by_class_tier.items():
        views = [float(r.get("views") or 0) for r in trows if float(r.get("views") or 0) > 0]
        ctx.class_tier_stats[(cc_id, tier)] = ContentClassTierViewStats(
            content_class_id=cc_id,
            creator_tier=tier,
            p50_views=_pct(views, 0.50),
            corpus_count=len(trows),
        )

    week_start = datetime.now(UTC).date() - timedelta(days=datetime.now(UTC).weekday())
    for nid in niche_ids:
        try:
            tv = (
                client.table("trend_velocity")
                .select("sound_trends")
                .eq("ingest_loop_niche_id", nid)
                .eq("week_start", week_start.isoformat())
                .maybe_single()
                .execute()
                .data
            )
        except Exception:
            tv = None
        bucket_map: dict[str, str] = {}
        if tv and isinstance(tv.get("sound_trends"), dict):
            st = tv["sound_trends"]
            for bucket in ("accelerating", "peaking", "cooling"):
                for item in st.get(bucket) or []:
                    sid = str(item.get("sound_id") or item.get("id") or "")
                    if sid:
                        bucket_map[sid] = bucket
        ctx.sound_momentum[nid] = bucket_map

    return ctx


def post_extract_should_reject(
    row: dict[str, Any],
    analysis: dict[str, Any],
    *,
    hook_type_counts: dict[str, int],
    breakout_ratio: float | None,
) -> tuple[bool, str]:
    """Tier 3 post-extract gate. Returns (reject, reason).

    Hard reject + hook cap apply only in ``purity`` mode so ``legacy`` nightly
    ingest stays byte-compatible until ``CORPUS_INGEST_MODE=purity``.
    """
    mode = corpus_ingest_mode()
    hard = settings.corpus_postextract_hard_reject and mode == "purity"
    hook_cap = settings.corpus_postextract_hook_cap_enforce and mode == "purity"
    if not hard and not hook_cap:
        return False, ""

    caption = str(row.get("caption") or "")
    if looks_like_non_vietnamese_caption(caption):
        return True, "non_vn_caption"

    inner = (analysis.get("analysis") or {}) if isinstance(analysis, dict) else {}
    hook_info = inner.get("hook_analysis") or {}
    hook_phrase = str(hook_info.get("hook_phrase") or row.get("hook_phrase") or "")
    scenes = inner.get("scenes") or []
    content_format = row.get("content_format")
    scene_count = int(row.get("scene_count") or len(scenes) or 0)

    if hard:
        if not content_format and scene_count < 2 and not hook_phrase:
            return True, "uninstructive_structure"

        topics = inner.get("topics") or []
        pain = inner.get("pain_points") or []
        transcript = str(inner.get("audio_transcript") or analysis.get("audio_transcript") or "")
        blob = " ".join(
            str(x) for x in [*topics, *pain, transcript, caption] if x
        ).lower()
        if hook_phrase and len(hook_phrase) > 8:
            tokens = [t for t in re.split(r"\W+", hook_phrase.lower()) if len(t) > 3]
            if tokens and not any(t in blob for t in tokens[:3]):
                return True, "hook_content_mismatch"

    if hook_cap:
        ht = str(row.get("hook_type") or "none")
        br = breakout_ratio or row.get("breakout_ratio") or 0.0
        try:
            br_f = float(br)
        except (TypeError, ValueError):
            br_f = 0.0
        count = hook_type_counts.get(ht, 0)
        if count >= settings.corpus_postextract_hook_cap and br_f < settings.corpus_hook_cap_breakout_bypass:
            return True, "hook_type_cap"

    return False, ""
