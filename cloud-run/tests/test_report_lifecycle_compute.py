"""Deterministic aggregator tests for lifecycle format mode.

The Gemini narrative layer is covered in ``test_report_lifecycle_gemini.py``;
this file pins the numeric shape of cells produced by
``compute_format_cells`` so a schema drift or taxonomy change can't
silently regress the stage classification.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_lifecycle_compute import (
    LIFECYCLE_SAMPLE_FLOOR,
    compute_format_cells,
    strip_internal_fields,
)


def _row(
    *,
    content_format: str,
    views: int,
    days_ago: int,
) -> dict[str, Any]:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "content_format": content_format,
        "views": views,
        "indexed_at": ts.isoformat(),
        "posted_at": ts.isoformat(),
    }


def _uniform_format(
    content_format: str,
    *,
    recent_views: int,
    prior_views: int,
    count_each: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Recent half (< 15 days ago on a 30-day window)
    for i in range(count_each):
        rows.append(_row(content_format=content_format, views=recent_views, days_ago=2 + i))
    # Prior half (> 15 days ago)
    for i in range(count_each):
        rows.append(_row(content_format=content_format, views=prior_views, days_ago=18 + i))
    return rows


def test_empty_corpus_returns_empty_cells() -> None:
    assert compute_format_cells([], window_days=30) == []


def test_format_with_too_few_samples_is_dropped() -> None:
    # Only 3 rows recent + 3 prior — below _FORMAT_MIN_SAMPLES (=5).
    rows = _uniform_format("tutorial", recent_views=1000, prior_views=1000, count_each=3)
    assert compute_format_cells(rows, window_days=30) == []


def test_rising_format_classified_correctly() -> None:
    # +30% week-over-week → rising (threshold ≥ +15%).
    rows = _uniform_format(
        "tutorial", recent_views=1300, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 1
    c = cells[0]
    assert c["stage"] == "rising"
    assert c["reach_delta_pct"] > 15.0
    assert c["health_score"] > 50


def test_peak_format_between_5_and_15_pct() -> None:
    rows = _uniform_format(
        "tutorial", recent_views=1100, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 1
    assert cells[0]["stage"] == "peak"


def test_plateau_format_within_5_pct_band() -> None:
    rows = _uniform_format(
        "tutorial", recent_views=1020, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 1
    assert cells[0]["stage"] == "plateau"


def test_declining_format_below_minus_5_pct() -> None:
    rows = _uniform_format(
        "tutorial", recent_views=800, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 1
    c = cells[0]
    assert c["stage"] == "declining"
    assert c["reach_delta_pct"] < -5.0
    assert c["health_score"] < 50


def test_multiple_formats_ranked_by_health() -> None:
    rows: list[dict[str, Any]] = []
    # Rising format — should rank first.
    rows += _uniform_format(
        "tutorial", recent_views=2000, prior_views=1000, count_each=6,
    )
    # Declining format — should rank last.
    rows += _uniform_format(
        "haul", recent_views=500, prior_views=1000, count_each=6,
    )
    # Plateau format — in the middle.
    rows += _uniform_format(
        "review", recent_views=1000, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 3
    # Rising health > plateau health > declining health.
    assert cells[0]["stage"] == "rising"
    assert cells[-1]["stage"] == "declining"


def test_internal_fields_present_before_strip() -> None:
    rows = _uniform_format(
        "tutorial", recent_views=2000, prior_views=1000, count_each=6,
    )
    cells = compute_format_cells(rows, window_days=30)
    assert "_recent_count" in cells[0]
    assert "_prior_count" in cells[0]

    clean = strip_internal_fields(cells)
    assert "_recent_count" not in clean[0]
    assert "_prior_count" not in clean[0]
    # Public fields unchanged.
    for k in ("name", "stage", "reach_delta_pct", "health_score", "insight"):
        assert k in clean[0]


def test_max_12_cells_when_taxonomy_saturated() -> None:
    """The content_format taxonomy has 15 values; LifecyclePayload caps
    ``cells`` at 12. The aggregator must clip."""
    rows: list[dict[str, Any]] = []
    formats = [
        "mukbang", "grwm", "recipe", "haul", "review",
        "tutorial", "comparison", "storytelling", "before_after", "pov",
        "outfit_transition", "vlog", "dance", "faceless", "other",
    ]
    for fmt in formats:
        # Every format rising with different magnitudes so ranks differ.
        multiplier = 1.0 + (formats.index(fmt) * 0.02)
        rows += _uniform_format(
            fmt,
            recent_views=int(1500 * multiplier),
            prior_views=1000,
            count_each=6,
        )
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) <= 12


def test_missing_content_format_falls_through_to_other() -> None:
    # Rows with no content_format key should still aggregate (as "other").
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for i in range(6):
        ts = (now - timedelta(days=2 + i)).isoformat()
        rows.append({"views": 1500, "indexed_at": ts})
    for i in range(6):
        ts = (now - timedelta(days=18 + i)).isoformat()
        rows.append({"views": 1000, "indexed_at": ts})
    cells = compute_format_cells(rows, window_days=30)
    assert len(cells) == 1
    assert "Khác" in cells[0]["name"] or "other" in cells[0]["name"].lower()


def test_sample_floor_constant_matches_other_reports() -> None:
    # Kept in sync with the timing / pattern thin-corpus gate so UI
    # behaviour ("mẫu thưa") lines up.
    assert LIFECYCLE_SAMPLE_FLOOR == 80
