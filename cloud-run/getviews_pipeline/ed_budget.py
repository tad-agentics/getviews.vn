"""Theoretical EnsembleData pool cost + unit estimates for [ed-meter] logs."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.config import (
    ED_UNIT_HASHTAG_POSTS,
    ED_UNIT_KEYWORD_SEARCH,
    ED_UNIT_POST_COMMENTS,
    ED_UNIT_POST_INFO,
    ED_UNIT_POST_MULTI_INFO,
    ED_UNIT_USER_POSTS,
    ED_UNIT_USER_SEARCH,
)


def endpoint_key_from_url(path_url: str) -> str:
    """Map full EnsembleData URL to a stable short key for counters."""
    u = path_url.lower()
    if "tt/keyword/search" in u:
        return "tt/keyword/search"
    if "tt/hashtag/posts" in u:
        return "tt/hashtag/posts"
    if "tt/post/multi-info" in u:
        return "tt/post/multi-info"
    if "tt/post/info" in u:
        return "tt/post/info"
    if "tt/post/comments" in u:
        return "tt/post/comments"
    if "tt/user/posts" in u:
        return "tt/user/posts"
    if "tt/user/search" in u:
        return "tt/user/search"
    return "other"


def unit_weight_for_endpoint(endpoint: str) -> float:
    """Return configured est_units multiplier per successful request."""
    if endpoint == "tt/keyword/search":
        return ED_UNIT_KEYWORD_SEARCH
    if endpoint == "tt/hashtag/posts":
        return ED_UNIT_HASHTAG_POSTS
    if endpoint == "tt/post/info":
        return ED_UNIT_POST_INFO
    if endpoint == "tt/post/multi-info":
        return ED_UNIT_POST_MULTI_INFO
    if endpoint == "tt/user/posts":
        return ED_UNIT_USER_POSTS
    if endpoint == "tt/user/search":
        return ED_UNIT_USER_SEARCH
    if endpoint == "tt/post/comments":
        return ED_UNIT_POST_COMMENTS
    return 1.0


def estimate_units_from_counts(counts: dict[str, int]) -> float:
    """``counts`` maps endpoint key → total requests (ok+err)."""
    total = 0.0
    for ep, n in counts.items():
        if n <= 0:
            continue
        total += float(n) * unit_weight_for_endpoint(ep)
    return total


def theoretical_ed_pool_requests(
    num_niches: int,
    *,
    keyword_pages: int,
    hashtag_limit: int,
    legacy_carousel_second_hashtag_pass: bool,
) -> dict[str, Any]:
    """Upper-bound pool-phase HTTP calls (excluding multi-info / post/info extras).

    Carousel legacy mode doubles hashtag fetches (video pool + carousel pool).
    """
    kw = max(0, num_niches) * max(0, keyword_pages)
    ht_mult = 2 if legacy_carousel_second_hashtag_pass else 1
    ht = max(0, num_niches) * max(0, hashtag_limit) * ht_mult
    return {
        "keyword_search_requests": kw,
        "hashtag_posts_requests": ht,
        "pool_http_total": kw + ht,
        "formula": f"niches={num_niches} * (keyword_pages={keyword_pages} + "
        f"hashtag_limit={hashtag_limit} * carousel_passes={ht_mult})",
    }
