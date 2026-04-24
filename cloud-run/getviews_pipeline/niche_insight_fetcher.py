"""Structured fetcher for ``niche_insights`` rows.

Closes state-of-corpus Appendix B Gap 2: the Layer 0 weekly cron
populates niche_insights (11 rows, one per niche, refreshed weekly)
but no Answer-session report module reads it today — so the most
actionable field (`execution_tip`) never surfaces in the UI.

This module bridges the gap. ``fetch_niche_insight(niche_id, *,
client)`` returns a ``NicheInsight`` Pydantic model (schema in
``report_types.py``) or ``None`` if no usable row exists.

Usability criteria — ALL must hold to return a non-None result:
  1. A row exists for the niche_id.
  2. ``quality_flag`` IS NULL (flagged rows intentionally skipped).
  3. Row age from ``week_of`` ≤ ``max_age_days`` (default 14).
  4. ``insight_text`` is non-empty (a row with every field null is
     pipeline noise; the injection has nothing to surface).

The existing ``pipelines._get_niche_insight`` is for the video
diagnosis flow and returns a pre-formatted prompt-injection string
for Gemini — this module returns structured data for Pattern +
Ideas payloads, where the UI renders the fields directly.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from getviews_pipeline.report_types import NicheInsight

logger = logging.getLogger(__name__)

# Layer 0 cron runs weekly; a row older than 14 days means at least
# one cron cycle has silently failed. Don't surface stale data as if
# it were fresh — let the UI render without the injection instead.
DEFAULT_MAX_AGE_DAYS = 14


def fetch_niche_insight(
    niche_id: int,
    *,
    client: Any,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    now: datetime | None = None,
) -> NicheInsight | None:
    """Fetch the latest usable ``niche_insights`` row and return it as
    a structured ``NicheInsight`` — or ``None`` if no row passes the
    4 usability gates documented at module level.

    Best-effort: any exception (DB down, schema drift, row malformed)
    logs a warning and returns ``None``. Never raises to the caller —
    the injection is additive; the report should render without it
    when it's not available.
    """
    if niche_id <= 0:
        return None

    try:
        resp = (
            client.table("niche_insights")
            .select(
                "week_of, insight_text, execution_tip, "
                "top_formula_hook, top_formula_format, "
                "staleness_risk, quality_flag",
            )
            .eq("niche_id", niche_id)
            .is_("quality_flag", None)
            .order("week_of", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[niche_insight_fetcher] query failed for niche_id=%d: %s", niche_id, exc)
        return None

    rows = resp.data or []
    if not rows:
        return None

    row = rows[0]
    insight_text = (row.get("insight_text") or "").strip()
    if not insight_text:
        # An empty-insight row carries no signal to surface.
        return None

    if not _is_fresh(row.get("week_of"), max_age_days=max_age_days, now=now):
        logger.info(
            "[niche_insight_fetcher] niche_id=%d row too stale (week_of=%s), skipping injection",
            niche_id, row.get("week_of"),
        )
        return None

    return NicheInsight(
        insight_text=insight_text,
        execution_tip=(row.get("execution_tip") or None),
        top_formula_hook=(row.get("top_formula_hook") or None),
        top_formula_format=(row.get("top_formula_format") or None),
        week_of=_format_week_of(row.get("week_of")),
        staleness_risk=_normalize_staleness(row.get("staleness_risk")),
    )


def _is_fresh(
    week_of_raw: Any,
    *,
    max_age_days: int,
    now: datetime | None = None,
) -> bool:
    """True if the week_of date is within ``max_age_days`` of today."""
    if not week_of_raw:
        return False
    now_ts = now or datetime.now(UTC)
    today = now_ts.date()
    try:
        if isinstance(week_of_raw, date):
            week_date = week_of_raw
        else:
            week_date = date.fromisoformat(str(week_of_raw)[:10])
    except ValueError:
        return False
    return (today - week_date) <= timedelta(days=max_age_days)


def _format_week_of(week_of_raw: Any) -> str | None:
    """Normalize to ``YYYY-MM-DD`` ISO string for wire stability."""
    if not week_of_raw:
        return None
    if isinstance(week_of_raw, date):
        return week_of_raw.isoformat()
    s = str(week_of_raw)[:10]
    # Validate it parses before returning — never ship a malformed
    # date string to the frontend.
    try:
        date.fromisoformat(s)
    except ValueError:
        return None
    return s


def _normalize_staleness(raw: Any) -> str | None:
    """Map arbitrary staleness_risk strings to the NicheInsight enum."""
    if not raw:
        return None
    s = str(raw).strip().upper()
    if s in ("LOW", "MODERATE", "HIGH"):
        return s
    return None
