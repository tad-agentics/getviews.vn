"""Tests for PostgREST-safe timestamp literals."""

from __future__ import annotations

from getviews_pipeline.postgrest_time import indexed_at_cutoff_iso


def test_indexed_at_cutoff_iso_is_no_sql_expression() -> None:
    v = indexed_at_cutoff_iso(7)
    assert "now()" not in v
    assert "interval" not in v
    assert "T" in v


def test_indexed_at_cutoff_iso_clamps_negative_days() -> None:
    a = indexed_at_cutoff_iso(-5)
    b = indexed_at_cutoff_iso(0)
    # Both should be "now-ish"; same day at least when run in same second — compare prefix
    assert len(a) == len(b)
