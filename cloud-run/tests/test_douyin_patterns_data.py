"""D5d (2026-06-05) — Kho Douyin · patterns read-model tests.

Mocks Supabase so tests don't hit the network. Covers:
  • Most-recent-week-per-niche collapse.
  • Deterministic (niche_id, rank) ordering after collapse.
  • Row serialization (sample_video_ids list, NULL-safe avg).
  • Defensive paths (query error → empty patterns).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.douyin_patterns_data import (
    _serialize_pattern,
    fetch_douyin_patterns,
)

# ── Mock helpers ────────────────────────────────────────────────────


def _patterns_chain(rows: list[dict[str, Any]] | Exception) -> MagicMock:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    if isinstance(rows, Exception):
        chain.execute.side_effect = rows
    else:
        chain.execute.return_value = MagicMock(data=rows)
    return chain


def _client(chain: MagicMock) -> MagicMock:
    client = MagicMock()
    client.table.return_value = chain
    return client


def _row(
    *,
    niche_id: int,
    week_of: str,
    rank: int,
    name_vn: str | None = None,
    cn_rise_pct_avg: float | None = 25.0,
) -> dict[str, Any]:
    return {
        "id": f"pat-{niche_id}-{week_of}-{rank}",
        "niche_id": niche_id,
        "week_of": week_of,
        "rank": rank,
        "name_vn": name_vn or f"Pattern {niche_id}/{rank}",
        "name_zh": "示例",
        "hook_template_vi": "3 việc trước khi ___",
        "format_signal_vi": "POV cận cảnh, transition cắt nhanh.",
        "sample_video_ids": [f"v{niche_id}-a", f"v{niche_id}-b", f"v{niche_id}-c"],
        "cn_rise_pct_avg": cn_rise_pct_avg,
        "computed_at": "2026-06-01T21:00:00+00:00",
    }


# ── _serialize_pattern ─────────────────────────────────────────────


def test_serialize_pattern_coerces_types_and_keeps_null_safe_defaults() -> None:
    out = _serialize_pattern(_row(niche_id=1, week_of="2026-06-01", rank=1))
    assert out["niche_id"] == 1
    assert out["week_of"] == "2026-06-01"
    assert out["rank"] == 1
    assert out["sample_video_ids"] == ["v1-a", "v1-b", "v1-c"]
    assert out["cn_rise_pct_avg"] == 25.0


def test_serialize_pattern_handles_null_cn_rise_pct_avg() -> None:
    row = _row(niche_id=1, week_of="2026-06-01", rank=1, cn_rise_pct_avg=None)
    assert _serialize_pattern(row)["cn_rise_pct_avg"] is None


def test_serialize_pattern_filters_empty_strings_from_sample_ids() -> None:
    row = _row(niche_id=1, week_of="2026-06-01", rank=1)
    row["sample_video_ids"] = ["v1", "  ", "", "v2", None]
    out = _serialize_pattern(row)
    assert out["sample_video_ids"] == ["v1", "v2"]


def test_serialize_pattern_handles_non_list_sample_ids() -> None:
    row = _row(niche_id=1, week_of="2026-06-01", rank=1)
    row["sample_video_ids"] = None
    assert _serialize_pattern(row)["sample_video_ids"] == []


# ── fetch_douyin_patterns — most-recent-week collapse ──────────────


def test_fetch_returns_empty_on_no_rows() -> None:
    client = _client(_patterns_chain([]))
    out = fetch_douyin_patterns(client)
    assert out == {"patterns": []}


def test_fetch_returns_only_most_recent_week_per_niche() -> None:
    """Niche 1 has rows in two weeks; niche 2 has rows in one week.
    The collapse must keep niche 1's MAX(week_of) batch + niche 2's
    only batch."""
    rows = [
        # Niche 1, 2026-06-08 (newer) — keep all 3
        _row(niche_id=1, week_of="2026-06-08", rank=1),
        _row(niche_id=1, week_of="2026-06-08", rank=2),
        _row(niche_id=1, week_of="2026-06-08", rank=3),
        # Niche 1, 2026-06-01 (older) — drop all 3
        _row(niche_id=1, week_of="2026-06-01", rank=1),
        _row(niche_id=1, week_of="2026-06-01", rank=2),
        _row(niche_id=1, week_of="2026-06-01", rank=3),
        # Niche 2, 2026-06-01 — keep all 3 (no newer week for this niche)
        _row(niche_id=2, week_of="2026-06-01", rank=1),
        _row(niche_id=2, week_of="2026-06-01", rank=2),
        _row(niche_id=2, week_of="2026-06-01", rank=3),
    ]
    client = _client(_patterns_chain(rows))
    out = fetch_douyin_patterns(client)
    weeks_per_niche = {(p["niche_id"], p["week_of"]) for p in out["patterns"]}
    assert weeks_per_niche == {
        (1, "2026-06-08"),
        (2, "2026-06-01"),
    }
    assert len(out["patterns"]) == 6


def test_fetch_orders_results_by_niche_id_then_rank() -> None:
    rows = [
        _row(niche_id=2, week_of="2026-06-01", rank=3),
        _row(niche_id=1, week_of="2026-06-01", rank=2),
        _row(niche_id=2, week_of="2026-06-01", rank=1),
        _row(niche_id=1, week_of="2026-06-01", rank=1),
        _row(niche_id=1, week_of="2026-06-01", rank=3),
        _row(niche_id=2, week_of="2026-06-01", rank=2),
    ]
    client = _client(_patterns_chain(rows))
    out = fetch_douyin_patterns(client)
    keys = [(p["niche_id"], p["rank"]) for p in out["patterns"]]
    assert keys == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]


def test_fetch_skips_rows_missing_niche_id_or_week_of() -> None:
    rows = [
        _row(niche_id=1, week_of="2026-06-01", rank=1),
        {**_row(niche_id=1, week_of="2026-06-01", rank=2), "niche_id": None},
        {**_row(niche_id=1, week_of="2026-06-01", rank=3), "week_of": None},
    ]
    client = _client(_patterns_chain(rows))
    out = fetch_douyin_patterns(client)
    assert len(out["patterns"]) == 1
    assert out["patterns"][0]["rank"] == 1


def test_fetch_returns_empty_on_query_error() -> None:
    """Defensive: a Supabase HTTP error must NOT crash the response —
    FE renders an empty §I state."""
    client = _client(_patterns_chain(RuntimeError("PostgREST 500")))
    assert fetch_douyin_patterns(client) == {"patterns": []}


def test_fetch_caps_at_200_rows() -> None:
    """Sanity: ``.limit(200)`` is the bounded query."""
    rows: list[dict[str, Any]] = []
    client = _client(_patterns_chain(rows))
    fetch_douyin_patterns(client)
    chain = client.table.return_value
    chain.limit.assert_called_with(200)


def test_fetch_orders_descending_week_then_ascending_niche_then_rank() -> None:
    """Sanity on the SQL order — week_of DESC + niche_id ASC + rank ASC."""
    client = _client(_patterns_chain([]))
    fetch_douyin_patterns(client)
    chain = client.table.return_value
    order_calls = [(c.args, c.kwargs) for c in chain.order.call_args_list]
    # Order: week_of DESC, niche_id ASC, rank ASC.
    assert order_calls[0][0] == ("week_of",)
    assert order_calls[0][1] == {"desc": True}
    assert order_calls[1][0] == ("niche_id",)
    assert order_calls[1][1] == {"desc": False}
    assert order_calls[2][0] == ("rank",)
    assert order_calls[2][1] == {"desc": False}
