"""Reference selection and trend velocity helpers (§4–§9)."""

from __future__ import annotations

import time
from typing import Any

# Tags that carry ZERO niche signal — appear equally across ALL niches.
# Keep this list short (~15). If a tag has any niche association, it belongs
# in niche_taxonomy.signal_hashtags instead of here.
GENERIC_HASHTAGS: frozenset[str] = frozenset({
    "fyp", "foryou", "foryoupage", "foryourpage", "fypage",
    "viral", "trending", "trend", "tiktok", "tiktokviral",
    "xyzbca", "blowthisup",
    "xuhuong", "thinhhanh", "hot",
})

# English niche-category words that are too broad to be useful for VN audience
# targeting. "#skincare" or "#fashion" appear across all niches on TikTok VN —
# the algorithm cannot use them to identify a Vietnamese target audience.
#
# Used in two places:
#   corpus_ingest.annotate_distribution()  — computes pct_has_specific_hashtags
#   hashtag_niche_map.learn_hashtag_mappings() — prevents learning false niche
#     associations from broad English category tags
#
# IMPORTANT: These tags are intentionally NOT in GENERIC_HASHTAGS.
# classify_from_hashtags() (read path) may legitimately match them against
# hashtag_niche_map DB rows that were seeded with high-quality signal data.
# Only the LEARNING path must block them — adding occurrences from corpus
# batch videos where "#skincare" co-occurs with a skincare niche fetch is
# circular and pollutes future classification.
DISTRIBUTION_GENERIC_HASHTAGS: frozenset[str] = GENERIC_HASHTAGS | frozenset({
    "ootd", "fashion", "beauty", "food", "funny", "comedy", "love",
    "music", "dance", "art", "photography", "travel", "fitness",
    "makeup", "skincare", "style", "outfit", "recipe", "diy",
    "learnontiktok", "edutok",
})


def infer_niche_from_hashtags(
    hashtags: list[str],
    description: str = "",
) -> str:
    """Pick the first non-generic hashtag, falling back to description snippet."""
    filtered = [h for h in hashtags if h.lower() not in GENERIC_HASHTAGS]
    if filtered:
        return filtered[0]
    desc = description.strip()[:40].strip()
    return desc if desc else "tiktok"


def _author_key(aweme: dict[str, Any]) -> str | None:
    author = aweme.get("author")
    if isinstance(author, dict):
        uid = author.get("uid") or author.get("id")
        if uid is not None:
            return str(uid)
        u = author.get("unique_id") or author.get("sec_uid")
        if u:
            return str(u)
    raw = aweme.get("author_user_id")
    return str(raw) if raw is not None else None


def _aweme_id(aweme: dict[str, Any]) -> str:
    return str(aweme.get("aweme_id", "") or "")


def _engagement_rate(aweme: dict[str, Any]) -> float:
    stats = aweme.get("statistics") or {}
    views = int(stats.get("play_count") or 0)
    if views <= 0:
        return 0.0
    eng = (
        int(stats.get("digg_count") or 0)
        + int(stats.get("comment_count") or 0)
        + int(stats.get("share_count") or 0)
    )
    return eng / views * 100.0


def select_reference_videos(
    search_results: list[dict[str, Any]],
    *,
    recency_days: int = 30,
    n: int = 3,
    cached_ids: set[str] | None = None,
    now: float | None = None,
    rank_by: str = "er",
) -> list[dict[str, Any]]:
    """Rank by ER or velocity; enforce creator diversity; recency window; skip cached ids."""
    t = now if now is not None else time.time()
    cutoff = t - (recency_days * 86400)
    skip = cached_ids or set()

    candidates = [
        v
        for v in search_results
        if _aweme_id(v) and _aweme_id(v) not in skip
    ]
    candidates = [
        v
        for v in candidates
        if int(v.get("create_time") or 0) >= int(cutoff)
    ]

    if rank_by == "velocity":
        candidates.sort(key=lambda v: velocity_score(v, now=t), reverse=True)
    else:
        candidates.sort(key=lambda v: _engagement_rate(v), reverse=True)
    seen_authors: set[str] = set()
    selected: list[dict[str, Any]] = []
    for v in candidates:
        ak = _author_key(v) or _aweme_id(v)
        if ak in seen_authors:
            continue
        seen_authors.add(ak)
        selected.append(v)
        if len(selected) >= n:
            break
    return selected


def velocity_score(aweme: dict[str, Any], *, now: float | None = None) -> float:
    """Lightweight momentum score for Intent 6 (ER weighted by recency)."""
    t = now if now is not None else time.time()
    ct = int(aweme.get("create_time") or 0)
    if ct <= 0:
        return 0.0
    age_hours = max((t - ct) / 3600.0, 0.5)
    er = _engagement_rate(aweme)
    return er / (age_hours**0.5)


def merge_aweme_lists(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by aweme_id preserving first-seen order."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for lst in lists:
        for a in lst:
            aid = _aweme_id(a)
            if not aid or aid in seen:
                continue
            seen.add(aid)
            out.append(a)
    return out


def filter_recency(
    awemes: list[dict[str, Any]],
    days: int,
    *,
    now: float | None = None,
) -> list[dict[str, Any]]:
    t = now if now is not None else time.time()
    cutoff = t - (days * 86400)
    return [a for a in awemes if int(a.get("create_time") or 0) >= int(cutoff)]
