"""Tests for corpus window settings + Vietnamese timeframe copy."""

from __future__ import annotations

from getviews_pipeline.corpus_windows import (
    corpus_adaptive_max_days,
    corpus_benchmark_window_days,
    corpus_citation_window_days,
    corpus_reference_fetch_days,
    corpus_reference_pick_days,
)
from getviews_pipeline.formatters import citation_vi, timeframe_vi


def test_default_corpus_windows_are_60() -> None:
    assert corpus_benchmark_window_days() == 60
    assert corpus_reference_fetch_days() == 60
    assert corpus_reference_pick_days() == 60
    assert corpus_citation_window_days() == 60
    assert corpus_adaptive_max_days() == 60


def test_timeframe_vi_60_is_two_months() -> None:
    assert timeframe_vi(60) == "2 tháng qua"
    assert timeframe_vi(45) == "2 tháng qua"
    assert timeframe_vi(61) == "3 tháng qua"


def test_citation_vi_uses_60_day_bucket() -> None:
    out = citation_vi(9127, "skincare", 60)
    assert "9.127" in out
    assert "2 tháng qua" in out
