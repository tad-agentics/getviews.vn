"""Layer 0A must not write dropped ``niche_insights`` columns."""

from __future__ import annotations

from getviews_pipeline.layer0_niche import NICHE_INSIGHT_UPSERT_COLUMNS


def test_niche_insight_upsert_columns_exclude_cross_niche_signals() -> None:
    assert "cross_niche_signals" not in NICHE_INSIGHT_UPSERT_COLUMNS


def test_niche_insight_upsert_columns_match_current_schema() -> None:
    assert set(NICHE_INSIGHT_UPSERT_COLUMNS) == {
        "niche_id",
        "week_of",
        "top_formula_hook",
        "top_formula_format",
        "insight_text",
        "mechanisms",
        "execution_tip",
        "staleness_risk",
        "quality_flag",
        "computed_at",
    }
