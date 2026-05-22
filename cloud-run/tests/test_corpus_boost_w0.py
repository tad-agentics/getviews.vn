"""Wave 0 — F8 verify: reference_eligible ref pool + boost_attribution ingest."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from getviews_pipeline.corpus_boost_suspect import BoostPercentiles, classify_boost_suspect


def test_boost_suspect_medium_not_reference_eligible() -> None:
    pct = BoostPercentiles(p75_views=20_000, p90_views=100_000, p25_er=2.0, thin=False)
    res = classify_boost_suspect(
        views=150_000,
        er=4.0,
        comments=0,
        percentiles=pct,
        hard_reject_enabled=False,
    )
    assert res.attribution == "suspect_medium"
    assert res.reference_eligible is False


def test_boost_organic_reference_eligible() -> None:
    pct = BoostPercentiles(p75_views=20_000, p90_views=100_000, p25_er=2.0, thin=False)
    res = classify_boost_suspect(
        views=5_000,
        er=8.0,
        comments=120,
        percentiles=pct,
        hard_reject_enabled=False,
    )
    assert res.reference_eligible is True


def test_fetch_corpus_reference_pool_sync_filters_reference_eligible() -> None:
    from getviews_pipeline.corpus_context import fetch_corpus_reference_pool_sync

    client = MagicMock()
    table = MagicMock()
    query = MagicMock()
    client.table.return_value = table
    table.select.return_value = query
    query.eq.return_value = query
    query.gte.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = MagicMock(data=[])

    with (
        patch("getviews_pipeline.corpus_context._anon_client", return_value=client),
        patch("getviews_pipeline.corpus_context._resolve_niche_id", return_value=1),
        patch(
            "getviews_pipeline.corpus_context._settings",
            MagicMock(corpus_boost_hard_reject=True),
        ),
    ):
        fetch_corpus_reference_pool_sync("Thời trang", days=30, limit=20)

    ref_eligible_calls = [
        c for c in query.eq.call_args_list if c.args == ("reference_eligible", True)
    ]
    assert ref_eligible_calls, "expected .eq('reference_eligible', True) when hard_reject on"
