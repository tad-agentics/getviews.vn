"""B.2.1 — match score helpers + /kol/browse assembly (no network).

D.1.3 additions at the bottom: match_score persistence contract
(cache hit / miss recompute / trigger-invalidated null).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.kol_browse import (
    _apply_follower_bounds,
    _apply_growth_fast_proxy,
    _is_fresh,
    _match_description_sentence,
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


def test_apply_follower_bounds() -> None:
    rows = [{"followers": 50_000}, {"followers": 500_000}, {"followers": 2_000_000}]
    out = _apply_follower_bounds(rows, 100_000, 1_000_000)
    assert [int(r["followers"]) for r in out] == [500_000]


def test_apply_growth_fast_proxy_keeps_upper_third() -> None:
    rows = [
        {"avg_views": 1000},
        {"avg_views": 2000},
        {"avg_views": 3000},
        {"avg_views": 4000},
        {"avg_views": 5000},
        {"avg_views": 6000},
    ]
    out = _apply_growth_fast_proxy(rows)
    assert len(out) < len(rows)
    assert all(float(r["avg_views"]) >= 4000 for r in out)


def test_match_description_sentence_includes_score() -> None:
    s = _match_description_sentence(82, "Skincare")
    assert "82" in s or "/100" in s
    assert "Skincare" in s


def test_run_kol_browse_search_filters_rows() -> None:
    """S-2 — partial handle + partial display_name substring match after decorate."""
    profile_exec = MagicMock(data={"primary_niche": 1, "reference_channel_handles": []})
    starters_exec = MagicMock(
        data=[
            {
                "handle": "alice",
                "display_name": "Alice Nguyen",
                "followers": 10_000,
                "avg_views": 5000,
                "video_count": 1,
                "rank": 1,
            },
            {
                "handle": "bobtech",
                "display_name": "Bob",
                "followers": 20_000,
                "avg_views": 8000,
                "video_count": 2,
                "rank": 2,
            },
        ]
    )
    tax_exec = MagicMock(data=[{"name_vn": "Tech", "name_en": "Tech"}])

    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "profiles":
            m.select.return_value.single.return_value.execute.return_value = profile_exec
        elif name == "starter_creators":
            m.select.return_value.eq.return_value.order.return_value.execute.return_value = starters_exec
        elif name == "niche_taxonomy":
            m.select.return_value.eq.return_value.limit.return_value.execute.return_value = tax_exec
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table

    out = run_kol_browse_sync(sb, niche_id=1, tab="discover", page=1, page_size=10, search="lice")
    assert out["total"] == 1
    assert out["rows"][0]["handle"] == "alice"

    out2 = run_kol_browse_sync(sb, niche_id=1, tab="discover", page=1, page_size=10, search="bob")
    assert out2["total"] == 1
    assert out2["rows"][0]["handle"] == "bobtech"

    out3 = run_kol_browse_sync(sb, niche_id=1, tab="discover", page=1, page_size=10, search="zzz")
    assert out3["total"] == 0
    assert out3["rows"] == []


# ── D.1.3 — match_score persistence contract ──────────────────────────────


def _build_basic_sb(
    *,
    primary_niche: int,
    starters: list[dict[str, object]],
    niche_label: str = "Tech",
    reference_handles: list[str] | None = None,
) -> MagicMock:
    """Minimal Supabase mock for kol_browse that does NOT route creator_velocity.

    Tests using this helper should monkeypatch _fetch_cached_match_scores
    + _writeback_match_scores so the cache path is stubbed cleanly.
    """
    profile_exec = MagicMock(
        data={
            "primary_niche": primary_niche,
            "reference_channel_handles": reference_handles or [],
        }
    )
    starters_exec = MagicMock(data=starters)
    tax_exec = MagicMock(data=[{"name_vn": niche_label, "name_en": niche_label}])
    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "profiles":
            m.select.return_value.single.return_value.execute.return_value = profile_exec
        elif name == "starter_creators":
            starter_chain = m.select.return_value.eq.return_value.order.return_value
            starter_chain.execute.return_value = starters_exec
        elif name == "niche_taxonomy":
            tax_chain = m.select.return_value.eq.return_value.limit.return_value
            tax_chain.execute.return_value = tax_exec
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


def test_match_score_cache_hit_uses_stored_value(monkeypatch) -> None:
    """Fresh cache (<7d) short-circuits compute_match_score; no writeback."""
    starters = [
        {
            "handle": "alice",
            "display_name": "Alice",
            "followers": 10_000,
            "avg_views": 5_000,
            "video_count": 1,
            "rank": 1,
        }
    ]
    sb = _build_basic_sb(primary_niche=1, starters=starters)

    fresh_ts = datetime.now(tz=timezone.utc) - timedelta(days=1)
    read_calls: list[int] = []
    writebacks: list[dict[str, int]] = []

    def fake_fetch(_sb: object, *, niche_id: int) -> dict[str, tuple[int, datetime]]:
        read_calls.append(niche_id)
        return {"alice": (42, fresh_ts)}

    def fake_writeback(_sb: object, *, niche_id: int, scores: dict[str, int], now=None) -> None:
        writebacks.append(dict(scores))

    monkeypatch.setattr("getviews_pipeline.kol_browse._fetch_cached_match_scores", fake_fetch)
    monkeypatch.setattr("getviews_pipeline.kol_browse._writeback_match_scores", fake_writeback)

    out = run_kol_browse_sync(sb, niche_id=1, tab="discover", page=1, page_size=10)

    assert read_calls == [1]
    assert out["rows"][0]["handle"] == "alice"
    # Cached 42 wins over whatever compute_match_score would produce.
    assert out["rows"][0]["match_score"] == 42
    # No misses → writeback payload is empty.
    assert writebacks == [{}]


def test_match_score_cache_miss_recomputes_and_writes_back(monkeypatch) -> None:
    """Empty cache → compute fresh score + writeback payload holds recomputed rows."""
    starters = [
        {
            "handle": "bobtech",
            "display_name": "Bob Tech",
            "followers": 20_000,
            "avg_views": 8_000,
            "video_count": 2,
            "rank": 1,
        }
    ]
    sb = _build_basic_sb(primary_niche=2, starters=starters)

    writebacks: list[dict[str, int]] = []

    def fake_fetch(_sb: object, *, niche_id: int) -> dict[str, tuple[int, datetime]]:
        return {}

    def fake_writeback(_sb: object, *, niche_id: int, scores: dict[str, int], now=None) -> None:
        writebacks.append(dict(scores))

    monkeypatch.setattr("getviews_pipeline.kol_browse._fetch_cached_match_scores", fake_fetch)
    monkeypatch.setattr("getviews_pipeline.kol_browse._writeback_match_scores", fake_writeback)

    out = run_kol_browse_sync(sb, niche_id=2, tab="discover", page=1, page_size=10)

    row = out["rows"][0]
    assert row["handle"] == "bobtech"
    assert isinstance(row["match_score"], int)
    assert 0 <= row["match_score"] <= 100
    # Recomputed score is queued for writeback (UPDATE creator_velocity).
    assert writebacks and "bobtech" in writebacks[0]
    assert writebacks[0]["bobtech"] == row["match_score"]


def test_trigger_invalidated_rows_are_filtered_and_recomputed(monkeypatch) -> None:
    """Post-trigger state: match_score = NULL rows are treated as miss.

    The Postgres trigger sets match_score + match_score_computed_at to NULL
    on profile change. _fetch_cached_match_scores must drop those rows so
    run_kol_browse_sync recomputes + writes a new value back.
    """
    from getviews_pipeline.kol_browse import _fetch_cached_match_scores

    # Simulate the Supabase select(...).eq(...).execute() chain returning
    # a mix of fresh, null-score, and null-timestamp rows.
    now = datetime.now(tz=timezone.utc)
    cv_rows = [
        {"creator_handle": "fresh", "match_score": 55, "match_score_computed_at": now.isoformat()},
        {"creator_handle": "trigger_nulled", "match_score": None, "match_score_computed_at": None},
        {"creator_handle": "timestamp_null", "match_score": 70, "match_score_computed_at": None},
    ]
    sb = MagicMock()
    cv_select = sb.table.return_value.select.return_value.eq.return_value
    cv_select.execute.return_value = MagicMock(data=cv_rows)

    cache = _fetch_cached_match_scores(sb, niche_id=9)

    # match_score IS NULL rows are excluded entirely.
    assert "trigger_nulled" not in cache
    # Fresh row lands with a parsed timestamp.
    assert "fresh" in cache and cache["fresh"][0] == 55
    assert cache["fresh"][1] is not None
    # NULL-timestamp row still enters the dict but _is_fresh(None) == False,
    # so run_kol_browse_sync will treat it as a miss.
    assert "timestamp_null" in cache and cache["timestamp_null"][1] is None
    assert _is_fresh(cache["timestamp_null"][1]) is False
    # Cross-check the TTL boundary behaviour for completeness.
    assert _is_fresh(now - timedelta(days=1)) is True
    assert _is_fresh(now - timedelta(days=8)) is False
    assert _is_fresh(None) is False
