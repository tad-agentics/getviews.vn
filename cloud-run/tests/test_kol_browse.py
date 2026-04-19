"""B.2.1 — match score helpers + /kol/browse assembly (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from getviews_pipeline.kol_browse import (
    compute_match_score,
    follower_range_overlap,
    growth_percentile_from_avgs,
    normalize_handle,
    reference_channel_overlap,
    run_kol_browse_sync,
)


def test_normalize_handle_strips_at_and_lowercases() -> None:
    assert normalize_handle("  @FooBar  ") == "foobar"


def test_follower_range_worked_example_bracket() -> None:
    """B.0.2 worked example: creator 412K vs user 50K → ~0.54 overlap."""
    out = follower_range_overlap(412_000, 50_000)
    assert 0.52 <= out <= 0.56


def test_follower_range_zero_when_gap_over_100x() -> None:
    assert follower_range_overlap(5_000_000, 50_000) == 0.0


def test_match_score_worked_example_close_to_plan() -> None:
    """Plan worked example shape; avg_views proxy replaces growth percentile."""
    niche_avgs = [10_000.0, 50_000.0, 89_000.0, 120_000.0]
    score = compute_match_score(
        creator_niche_id=3,
        user_niche_id=3,
        creator_followers=412_000,
        user_followers=50_000,
        creator_avg_views=89_000.0,
        niche_avg_views=niche_avgs,
        reference_handles=["sammie"],
        starter_handles_in_niche={"sammie", "other"},
    )
    assert score == 81


def test_reference_channel_overlap_half() -> None:
    assert reference_channel_overlap(["a", "b"], {"a"}) == 0.5


def test_growth_percentile_endpoints() -> None:
    assert growth_percentile_from_avgs(10.0, [1.0, 2.0, 10.0]) == 1.0
    assert growth_percentile_from_avgs(1.0, [1.0, 2.0, 10.0]) == pytest.approx(1.0 / 3.0)


def test_run_kol_browse_discover_requires_primary_niche() -> None:
    sb = MagicMock()
    sb.table.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
        data={"primary_niche": None, "reference_channel_handles": []}
    )
    with pytest.raises(ValueError, match="Chưa chọn ngách"):
        run_kol_browse_sync(sb, niche_id=3, tab="discover", page=1, page_size=10)


def test_run_kol_browse_niche_mismatch() -> None:
    sb = MagicMock()
    sb.table.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
        data={"primary_niche": 5, "reference_channel_handles": []}
    )
    with pytest.raises(ValueError, match="không khớp"):
        run_kol_browse_sync(sb, niche_id=3, tab="discover", page=1, page_size=10)
