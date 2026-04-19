"""EnsembleData metering helpers — theoretical pool budget + endpoint keys."""

from __future__ import annotations

from getviews_pipeline.ed_budget import (
    endpoint_key_from_url,
    estimate_units_from_counts,
    theoretical_ed_pool_requests,
)


def test_endpoint_key_from_url() -> None:
    assert (
        endpoint_key_from_url("https://ensembledata.com/apis/tt/keyword/search")
        == "tt/keyword/search"
    )
    assert (
        endpoint_key_from_url("https://ensembledata.com/apis/tt/hashtag/posts")
        == "tt/hashtag/posts"
    )
    assert endpoint_key_from_url("https://ensembledata.com/apis/tt/post/multi-info") == (
        "tt/post/multi-info"
    )


def test_estimate_units_from_counts_defaults() -> None:
    est = estimate_units_from_counts({"tt/hashtag/posts": 10, "tt/keyword/search": 5})
    assert est == 15.0


def test_theoretical_pool_default_21_niches() -> None:
    """Default corpus caps: 21 niches × (2 keyword pages + 6 hashtag, single carousel pass)."""
    niches = 21
    kw_pages = 2
    ht_limit = 6
    t = theoretical_ed_pool_requests(
        niches,
        keyword_pages=kw_pages,
        hashtag_limit=ht_limit,
        legacy_carousel_second_hashtag_pass=False,
    )
    assert t["keyword_search_requests"] == niches * kw_pages
    assert t["hashtag_posts_requests"] == niches * ht_limit
    assert t["pool_http_total"] == niches * (kw_pages + ht_limit)
    # PR review aid — if BATCH_* defaults change, update this test.
    assert t["pool_http_total"] == 168


def test_theoretical_pool_legacy_carousel_doubles_hashtag() -> None:
    t = theoretical_ed_pool_requests(
        21,
        keyword_pages=2,
        hashtag_limit=6,
        legacy_carousel_second_hashtag_pass=True,
    )
    assert t["hashtag_posts_requests"] == 21 * 6 * 2
    assert t["pool_http_total"] == 21 * (2 + 12)
