"""Literal timestamps for PostgREST ``.gte`` / ``.lte`` filters.

PostgREST sends comparison values as bound parameters; strings like
``now() - interval '7 days'`` are not valid ``timestamptz`` literals and
yield 400 from Postgres (BUG-11). Compute cutoffs in Python instead.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def indexed_at_cutoff_iso(days: int) -> str:
    """Return ISO-8601 UTC ``indexed_at >=`` cutoff for the last ``days`` days."""
    if days < 0:
        days = 0
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()
