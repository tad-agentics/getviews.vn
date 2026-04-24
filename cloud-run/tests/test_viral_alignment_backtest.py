"""Wave 3 PR #4 — viral-alignment backtest harness tests.

Pins:

* ``compute_viral_score`` — formula math, low-sample guard, missing-
  field guard, circular-hour time alignment (23h vs 0h = 1h apart).
* ``spearman_rho`` + ``_ranks`` + ``_pearson`` — pure-Python stats
  helpers must match known-good values within floating-point tolerance.
* ``histogram`` + ``quantiles`` — deterministic shape, handles empty
  input, keeps zero-count buckets.
* ``run_viral_score_backtest`` — integration against a MagicMock client
  that fakes the scoreable-rows SELECT; must produce a well-formed
  summary including the spearman_gate_met flag.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.viral_alignment_backtest import (
    NICHE_MIN_SAMPLE,
    TOP_N,
    ViralScoreInputs,
    ViralScoreResult,
    _pearson,
    _ranks,
    compute_viral_score,
    histogram,
    quantiles,
    run_viral_score_backtest,
    spearman_rho,
)

# ── _ranks — average-rank tie handling ───────────────────────────────

def test_ranks_no_ties() -> None:
    assert _ranks([10.0, 20.0, 30.0]) == [1.0, 2.0, 3.0]


def test_ranks_with_ties_use_midpoint() -> None:
    # Two-way tie at the bottom → both get rank 1.5.
    assert _ranks([5.0, 5.0, 10.0]) == [1.5, 1.5, 3.0]


def test_ranks_all_tied() -> None:
    assert _ranks([7.0, 7.0, 7.0, 7.0]) == [2.5, 2.5, 2.5, 2.5]


def test_ranks_empty() -> None:
    assert _ranks([]) == []


# ── _pearson — reference values ──────────────────────────────────────

def test_pearson_perfect_positive() -> None:
    assert _pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) == pytest.approx(1.0)


def test_pearson_perfect_negative() -> None:
    assert _pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2]) == pytest.approx(-1.0)


def test_pearson_constant_input_returns_zero() -> None:
    """Constant variable → Pearson undefined; helper returns 0.0."""
    assert _pearson([1, 1, 1], [1, 2, 3]) == 0.0
    assert _pearson([1, 2, 3], [5, 5, 5]) == 0.0


def test_pearson_degenerate_lengths_return_zero() -> None:
    assert _pearson([1], [2]) == 0.0
    assert _pearson([], []) == 0.0


# ── spearman_rho — monotone-but-not-linear ──────────────────────────

def test_spearman_rho_is_1_on_monotone_nonlinear() -> None:
    """y = x^3 is non-linear in Pearson but rank-1.0 in Spearman."""
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [1.0, 8.0, 27.0, 64.0, 125.0]
    assert spearman_rho(xs, ys) == pytest.approx(1.0)


def test_spearman_rho_is_minus_1_on_monotone_decreasing() -> None:
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [10.0, 9.0, 8.0, 7.0]
    assert spearman_rho(xs, ys) == pytest.approx(-1.0)


def test_spearman_rho_zero_on_unrelated() -> None:
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [3.0, 3.0, 3.0, 3.0]  # constant → undefined → returns 0
    assert spearman_rho(xs, ys) == 0.0


# ── histogram ────────────────────────────────────────────────────────

def test_histogram_empty_still_has_10_bins() -> None:
    h = histogram([])
    assert len(h) == 10
    assert all(b["count"] == 0 for b in h)


def test_histogram_bucket_edges() -> None:
    # One score at every bin boundary — the implementation puts
    # boundary values in the lower bucket (so 100 lands in 90-100, not
    # a 101+ overflow).
    scores = [0, 10, 50, 99, 100]
    h = histogram(scores)
    # Decode counts by bin label for readability.
    counts = {b["bin"]: b["count"] for b in h}
    assert counts["0-10"] == 1       # 0
    assert counts["10-20"] == 1      # 10 falls here (int(10/10)=1)
    assert counts["50-60"] == 1      # 50
    assert counts["90-100"] == 2     # 99 + 100


def test_histogram_bins_preserve_order() -> None:
    h = histogram([50])
    assert [b["bin"] for b in h] == [
        "0-10", "10-20", "20-30", "30-40", "40-50",
        "50-60", "60-70", "70-80", "80-90", "90-100",
    ]


# ── quantiles ────────────────────────────────────────────────────────

def test_quantiles_empty_returns_empty_dict() -> None:
    assert quantiles([]) == {}


def test_quantiles_single_value() -> None:
    q = quantiles([50])
    assert q["min"] == q["max"] == q["p50"] == 50.0


def test_quantiles_monotone_p50() -> None:
    q = quantiles([10, 20, 30, 40, 50])
    assert q["p50"] == 30.0
    assert q["min"] == 10.0
    assert q["max"] == 50.0
    assert q["mean"] == 30.0


# ── compute_viral_score — formula math ──────────────────────────────

def _make_niche_pool(
    hook_types: list[str], formats: list[str], hours: list[int],
) -> list[dict[str, Any]]:
    """Build a fake top-30 niche pool. Lengths must match TOP_N."""
    assert len(hook_types) == len(formats) == len(hours) == TOP_N
    return [
        {"hook_type": h, "content_format": f, "posting_hour": hr}
        for h, f, hr in zip(hook_types, formats, hours, strict=True)
    ]


def test_score_perfect_match_caps_at_100() -> None:
    """All 30 niche videos have hook X + format Y, peak hour 18,
    sample also (X, Y, 18) → 100."""
    pool = _make_niche_pool(
        hook_types=["question"] * TOP_N,
        formats=["review"] * TOP_N,
        hours=[18] * TOP_N,
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=18)
    assert r.score == 100
    assert r.hook_alignment == 1.0
    assert r.format_alignment == 1.0
    assert r.time_alignment == 1.0
    assert len(r.reasons) == 3
    assert r.insufficient_reason is None


def test_score_no_match_is_zero() -> None:
    pool = _make_niche_pool(
        hook_types=["other"] * TOP_N,
        formats=["other_fmt"] * TOP_N,
        hours=[3] * TOP_N,
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    # peak_hour 3; sample 18; diff = 9h >> 6h window → time_alignment 0.
    r = compute_viral_score(inputs, pool, niche_peak_hour=3)
    assert r.score == 0
    assert r.hook_alignment == 0.0
    assert r.format_alignment == 0.0
    assert r.time_alignment == 0.0


def test_score_weighted_sum_matches_spec() -> None:
    """Spec: w_hook=0.5, w_format=0.3, w_time=0.2.
    15/30 hook + 9/30 format + 0 time = 0.5*0.5 + 0.3*0.3 + 0.2*0 = 0.34 → 34."""
    pool = _make_niche_pool(
        hook_types=["question"] * 15 + ["other"] * 15,
        formats=["review"] * 9 + ["other_fmt"] * 21,
        hours=[3] * TOP_N,
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=3)
    # Time: abs(18-3) = 15h, clock distance min(15, 24-15) = 9h > 6h → 0.
    assert r.score == 34


def test_score_time_alignment_is_circular() -> None:
    """23h vs 0h should be 1h apart, not 23h apart (clock wraps)."""
    pool = _make_niche_pool(
        hook_types=["question"] * TOP_N,
        formats=["review"] * TOP_N,
        hours=[0] * TOP_N,
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=23,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=0)
    # diff = 1h; time_align = 1 - 1/6 = 0.833
    assert r.time_alignment == pytest.approx(0.833, abs=0.01)


def test_score_insufficient_niche_sample() -> None:
    """Niche pool < 30 rows → None + reason=insufficient_niche_sample."""
    pool = [{"hook_type": "question", "content_format": "review", "posting_hour": 18}] * 15
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=18)
    assert r.score is None
    assert r.insufficient_reason == "insufficient_niche_sample"
    assert r.reasons == []


def test_score_missing_hook_type_is_null_not_zero() -> None:
    pool = _make_niche_pool(["x"] * TOP_N, ["y"] * TOP_N, [18] * TOP_N)
    inputs = ViralScoreInputs(
        niche_id=1, hook_type=None, content_format="y", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, 18)
    assert r.score is None
    assert r.insufficient_reason == "missing_hook_type"


def test_score_missing_content_format_is_null_not_zero() -> None:
    pool = _make_niche_pool(["x"] * TOP_N, ["y"] * TOP_N, [18] * TOP_N)
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="x", content_format=None, posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, 18)
    assert r.score is None
    assert r.insufficient_reason == "missing_content_format"


def test_score_null_peak_hour_zeroes_time_dim_but_still_scores() -> None:
    """A niche with no peak hour (all posting_hour NULL) still produces
    a hook+format score — time dimension contributes 0. Reason bullet
    explains."""
    pool = _make_niche_pool(
        hook_types=["question"] * TOP_N,
        formats=["review"] * TOP_N,
        hours=[18] * TOP_N,
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=None)
    # 1.0 * 0.5 + 1.0 * 0.3 + 0 * 0.2 = 0.8 → 80
    assert r.score == 80
    assert r.time_alignment == 0.0
    assert "bỏ qua tín hiệu thời điểm" in r.reasons[2].lower()


def test_score_uses_first_top_n_when_pool_is_larger() -> None:
    """Extra rows beyond TOP_N must not inflate the denominator."""
    # 60 rows, only the first 30 match — hook_alignment = 30/30, not 30/60.
    pool = (
        [{"hook_type": "question", "content_format": "review", "posting_hour": 18}] * TOP_N
        + [{"hook_type": "other", "content_format": "other", "posting_hour": 3}] * TOP_N
    )
    inputs = ViralScoreInputs(
        niche_id=1, hook_type="question", content_format="review", posting_hour=18,
    )
    r = compute_viral_score(inputs, pool, niche_peak_hour=18)
    assert r.hook_alignment == 1.0
    assert r.score == 100


# ── Harness integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backtest_harness_reports_well_formed_summary() -> None:
    """End-to-end with a mocked client. Builds 60 rows across 2 niches
    (one scoreable at 35 rows, one low-sample at 25), samples 40,
    expects non-zero scored + non-zero insufficient counts."""
    rows: list[dict[str, Any]] = []
    # Niche 7 — 35 rows, varying hook/format/hour so the correlation
    # isn't degenerate (all same score).
    for i in range(35):
        rows.append({
            "video_id": f"v7_{i}",
            "niche_id": 7,
            "hook_type": "question" if i % 2 == 0 else "bold_claim",
            "content_format": "review" if i % 3 == 0 else "tutorial",
            "posting_hour": 18 if i < 20 else 21,  # peak = 18
            "breakout_multiplier": 1.0 + i * 0.1,
        })
    # Niche 99 — 25 rows (below NICHE_MIN_SAMPLE).
    for i in range(25):
        rows.append({
            "video_id": f"v99_{i}",
            "niche_id": 99,
            "hook_type": "question",
            "content_format": "review",
            "posting_hour": 18,
            "breakout_multiplier": 1.0,
        })

    chain = MagicMock()
    chain.select.return_value = chain
    chain.not_.is_.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=rows)

    client = MagicMock()
    client.table.return_value = chain

    summary = await run_viral_score_backtest(client, sample_size=40, seed=1)

    assert summary["sample_size"] == 40
    # Total = scored + insufficient.
    assert summary["scored_count"] + summary["insufficient_count"] == 40
    # Niche 99 samples all flow to insufficient_niche_sample.
    assert "insufficient_niche_sample" in summary["insufficient_reasons"]
    # Histogram has all 10 bins.
    assert len(summary["distribution"]) == 10
    # Quantiles populated when there's at least one score.
    if summary["scored_count"] > 0:
        assert "p50" in summary["quantiles"]
    # Weights echoed for audit.
    assert summary["weights"]["hook"] == 0.5
    # Gate metadata present even when not met (small sample → ρ noisy).
    assert "spearman_gate" in summary
    assert summary["spearman_gate"] == 0.35
    assert isinstance(summary["spearman_gate_met"], bool)
    # Per-niche breakdown includes only scored niches.
    niches = {pn["niche_id"] for pn in summary["per_niche"]}
    assert 7 in niches
    assert 99 not in niches
    # Seed echoed so the doc can cite reproducibility.
    assert summary["seed"] == 1


@pytest.mark.asyncio
async def test_backtest_harness_handles_empty_corpus() -> None:
    """Zero scoreable rows → well-formed zero-shape summary."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.not_.is_.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=[])

    client = MagicMock()
    client.table.return_value = chain

    summary = await run_viral_score_backtest(client, sample_size=50, seed=7)
    assert summary["sample_size"] == 0
    assert summary["scored_count"] == 0
    # Histogram still rendered with 10 zero buckets — stable x-axis.
    assert len(summary["distribution"]) == 10
    assert all(b["count"] == 0 for b in summary["distribution"])
    assert summary["quantiles"] == {}


# ── Module constants — make the design doc spec auditable ──────────


def test_weights_sum_to_one() -> None:
    from getviews_pipeline.viral_alignment_backtest import W_FORMAT, W_HOOK, W_TIME

    assert W_HOOK + W_FORMAT + W_TIME == pytest.approx(1.0)


def test_top_n_and_min_sample_match_spec() -> None:
    # Wave 3 spec says top-30 / min-sample 30. Keep them wired together
    # so a future tune affects both.
    assert TOP_N == 30
    assert NICHE_MIN_SAMPLE == 30


def test_viral_score_result_to_dict_round_trip() -> None:
    r = ViralScoreResult(
        score=75, hook_alignment=0.6, format_alignment=0.4,
        time_alignment=0.8, reasons=["a", "b", "c"], insufficient_reason=None,
    )
    d = r.to_dict()
    assert d["score"] == 75
    assert d["reasons"] == ["a", "b", "c"]
    assert d["insufficient_reason"] is None
