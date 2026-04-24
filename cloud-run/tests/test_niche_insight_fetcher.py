"""Unit tests for ``niche_insight_fetcher.fetch_niche_insight``.

Pins the 4 usability gates documented at the module level + the 3
normalization helpers (date formatting, staleness enum coercion,
graceful degradation on DB errors).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.niche_insight_fetcher import (
    DEFAULT_MAX_AGE_DAYS,
    _format_week_of,
    _is_fresh,
    _normalize_staleness,
    fetch_niche_insight,
)


def _client_returning(rows: list[dict[str, Any]]) -> MagicMock:
    """Build a Supabase mock for the full chain:
    client.table(x).select(y).eq(...).is_(...).order(...).limit(...).execute()"""
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain = chain.eq.return_value.is_.return_value.order.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=rows)
    return client


def _row(**overrides: Any) -> dict[str, Any]:
    """Baseline usable row — a fresh, quality-passing insight."""
    return {
        "week_of": (datetime.now(UTC).date() - timedelta(days=3)).isoformat(),
        "insight_text": "Hook-cảm xúc + mukbang đang dẫn đầu trong tuần.",
        "execution_tip": "Thử mở bằng 'Bạn đã bao giờ...' trên video tiếp theo.",
        "top_formula_hook": "question",
        "top_formula_format": "mukbang",
        "staleness_risk": "LOW",
        "quality_flag": None,
        **overrides,
    }


# ── Happy path ───────────────────────────────────────────────────────

def test_fresh_quality_row_returns_structured_insight() -> None:
    client = _client_returning([_row()])
    result = fetch_niche_insight(niche_id=4, client=client)

    assert result is not None
    assert result.insight_text.startswith("Hook-cảm xúc")
    assert result.execution_tip.startswith("Thử mở bằng")
    assert result.top_formula_hook == "question"
    assert result.top_formula_format == "mukbang"
    assert result.staleness_risk == "LOW"
    # week_of normalized to ISO string
    assert len(result.week_of) == 10 and result.week_of[4] == "-"


# ── Usability gates ──────────────────────────────────────────────────

def test_no_rows_returns_none() -> None:
    client = _client_returning([])
    assert fetch_niche_insight(niche_id=4, client=client) is None


def test_zero_or_negative_niche_id_short_circuits() -> None:
    """Never issue the query for sentinel niche ids."""
    client = MagicMock()
    assert fetch_niche_insight(niche_id=0, client=client) is None
    assert fetch_niche_insight(niche_id=-1, client=client) is None
    client.table.assert_not_called()


def test_empty_insight_text_returns_none() -> None:
    """A row with everything-else populated but insight_text blank is
    pipeline noise — nothing to surface."""
    client = _client_returning([_row(insight_text="")])
    assert fetch_niche_insight(niche_id=4, client=client) is None


def test_whitespace_only_insight_text_returns_none() -> None:
    client = _client_returning([_row(insight_text="   \n\t")])
    assert fetch_niche_insight(niche_id=4, client=client) is None


def test_stale_row_returns_none() -> None:
    """Row older than max_age_days is rejected even with good data —
    surfacing stale insights as fresh erodes trust."""
    stale = (datetime.now(UTC).date() - timedelta(days=DEFAULT_MAX_AGE_DAYS + 1)).isoformat()
    client = _client_returning([_row(week_of=stale)])
    assert fetch_niche_insight(niche_id=4, client=client) is None


def test_boundary_age_accepted() -> None:
    """Exactly at max_age_days is still acceptable (inclusive boundary)."""
    boundary = (datetime.now(UTC).date() - timedelta(days=DEFAULT_MAX_AGE_DAYS)).isoformat()
    client = _client_returning([_row(week_of=boundary)])
    assert fetch_niche_insight(niche_id=4, client=client) is not None


def test_custom_max_age_honored() -> None:
    """Operator can tighten the freshness gate per-call."""
    row_age_5d = (datetime.now(UTC).date() - timedelta(days=5)).isoformat()
    client = _client_returning([_row(week_of=row_age_5d)])
    # Default 14d window: accept
    assert fetch_niche_insight(niche_id=4, client=client) is not None
    # Tight 3d window: reject
    client2 = _client_returning([_row(week_of=row_age_5d)])
    assert fetch_niche_insight(niche_id=4, client=client2, max_age_days=3) is None


# ── DB error isolation ──────────────────────────────────────────────

def test_query_exception_returns_none_not_raises() -> None:
    """Injection is additive — DB flake should never break the caller."""
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain = chain.eq.return_value.is_.return_value.order.return_value.limit.return_value
    chain.execute.side_effect = RuntimeError("supabase down")

    # Must not raise.
    assert fetch_niche_insight(niche_id=4, client=client) is None


# ── Normalization helpers ───────────────────────────────────────────

def test_is_fresh_accepts_date_objects_and_strings() -> None:
    today = datetime.now(UTC).date()
    assert _is_fresh(today, max_age_days=7) is True
    assert _is_fresh(today.isoformat(), max_age_days=7) is True
    assert _is_fresh((today - timedelta(days=30)).isoformat(), max_age_days=7) is False


def test_is_fresh_malformed_input_is_not_fresh() -> None:
    assert _is_fresh(None, max_age_days=7) is False
    assert _is_fresh("", max_age_days=7) is False
    assert _is_fresh("not-a-date", max_age_days=7) is False


def test_format_week_of_normalizes_to_iso() -> None:
    assert _format_week_of(date(2026, 5, 1)) == "2026-05-01"
    assert _format_week_of("2026-05-01T00:00:00Z") == "2026-05-01"
    assert _format_week_of("garbage") is None
    assert _format_week_of(None) is None


def test_normalize_staleness_enum_coercion() -> None:
    assert _normalize_staleness("LOW") == "LOW"
    assert _normalize_staleness("low") == "LOW"
    assert _normalize_staleness("  moderate ") == "MODERATE"
    assert _normalize_staleness("HIGH") == "HIGH"
    # Unknown values coerce to None rather than polluting the enum
    assert _normalize_staleness("critical") is None
    assert _normalize_staleness("") is None
    assert _normalize_staleness(None) is None
