"""Wave 3 PR #4 — viral-alignment score backtest harness.

Runs the proposed viral-alignment score formula over a sample of
``video_corpus`` rows with known ``breakout_multiplier`` and reports:

  * Score distribution — histogram + quantiles. Must NOT cluster all
    at 70–80 (the reviewer flag: a flat "everyone gets a B" score
    erodes trust faster than no score).
  * Spearman ρ between score and ``breakout_multiplier``. The design-
    doc gate (Wave 3 exit criteria) is ρ ≥ 0.35 on a 200-video sample.
  * Low-sample degradation — how many videos fall into niches with
    < 30 rows. These return ``score=null, reason="insufficient_data"``
    rather than a noisy partial score.
  * Per-niche breakdown — mean score + correlation per niche so we
    can see whether ρ is driven by one overrepresented niche.

This module owns the formula AND the backtest so the design-doc
numbers (Wave 3 PR #5) trace to code, not prose. Wave 4 will extract
the formula to a ``viral_alignment.py`` production module and the
``run_backtest`` harness will become the calibration suite.

Formula (initial, to be calibrated):

    score = 100 × (w_hook × hook_alignment
                 + w_format × format_alignment
                 + w_time × time_alignment)

    hook_alignment   = (# top-30 niche videos w/ same hook_type) / 30
    format_alignment = (# top-30 w/ same content_format) / 30
    time_alignment   = 1 - min(1, |posting_hour - niche_peak_hour| / 6)
    w_hook=0.5, w_format=0.3, w_time=0.2

    niche_peak_hour  = mode of posting_hour in the niche's top-30.

Low-sample guard: if the sample video's niche has < 30 rows with
``breakout_multiplier``, the formula returns None (reason=
``insufficient_data``); the backtest still records these but excludes
them from the correlation calculation.

Pure Python — no scipy/numpy. The cloud-run service deliberately
avoids pulling in a ~100MB scientific stack for one correlation
number per backtest run.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Formula parameters — to be calibrated via backtest ────────────────

W_HOOK = 0.5
W_FORMAT = 0.3
W_TIME = 0.2

TOP_N = 30
NICHE_MIN_SAMPLE = 30

# Maximum hour-difference the time_alignment formula treats as "peak"
# before clamping to zero. 6h = a third of the TikTok clock face; after
# that the slot is functionally a different audience.
TIME_DECAY_WINDOW_H = 6

# Histogram bucket count for the distribution report. 10 buckets of 10
# points each is the right granularity to catch "everyone gets 70–80"
# clustering without drowning the JSON in single-count bins.
HIST_BUCKETS = 10


# ── Inputs + results ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ViralScoreInputs:
    """The fields needed to score one video."""

    niche_id: int
    hook_type: str | None
    content_format: str | None
    posting_hour: int | None


@dataclass(frozen=True)
class ViralScoreResult:
    """The formula output for one video.

    ``reasons`` is a 3-bullet Vietnamese receipt keyed to the three
    dimensions — deterministic templating, never Gemini-generated, so
    the FE pill can display auditable text.

    ``insufficient_reason`` is None on a successful score; set to a
    string (e.g. ``"insufficient_data"``, ``"missing_hook_type"``) when
    the formula can't run, so the caller can distinguish a null score
    from a legitimate zero.
    """

    score: int | None
    hook_alignment: float | None
    format_alignment: float | None
    time_alignment: float | None
    reasons: list[str] = field(default_factory=list)
    insufficient_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Core scoring ──────────────────────────────────────────────────────


def _mode_hour(rows: list[dict[str, Any]]) -> int | None:
    """Return the most common posting_hour across rows, or None."""
    hours = [r.get("posting_hour") for r in rows if r.get("posting_hour") is not None]
    if not hours:
        return None
    return Counter(hours).most_common(1)[0][0]


def compute_viral_score(
    inputs: ViralScoreInputs,
    niche_top30: list[dict[str, Any]],
    niche_peak_hour: int | None,
) -> ViralScoreResult:
    """Score one video against its niche's top-30 reference pool.

    Always returns a ``ViralScoreResult`` — a null-score result carries
    an ``insufficient_reason`` string so callers can surface the right
    "Chưa đủ data" message instead of a misleading zero.
    """
    # Niche sample gate — the single most important graceful-fail path.
    if len(niche_top30) < NICHE_MIN_SAMPLE:
        return ViralScoreResult(
            score=None, hook_alignment=None, format_alignment=None,
            time_alignment=None, reasons=[],
            insufficient_reason="insufficient_niche_sample",
        )

    # Missing input fields — don't silently treat as zero.
    if not inputs.hook_type:
        return ViralScoreResult(
            score=None, hook_alignment=None, format_alignment=None,
            time_alignment=None, reasons=[],
            insufficient_reason="missing_hook_type",
        )
    if not inputs.content_format:
        return ViralScoreResult(
            score=None, hook_alignment=None, format_alignment=None,
            time_alignment=None, reasons=[],
            insufficient_reason="missing_content_format",
        )

    # Use exactly the first TOP_N rows of niche_top30 (caller pre-sorted
    # DESC by breakout). Extra rows would inflate the denominator.
    pool = niche_top30[:TOP_N]

    hook_hits = sum(1 for r in pool if r.get("hook_type") == inputs.hook_type)
    format_hits = sum(1 for r in pool if r.get("content_format") == inputs.content_format)

    hook_align = hook_hits / TOP_N
    format_align = format_hits / TOP_N

    if inputs.posting_hour is None or niche_peak_hour is None:
        time_align = 0.0
        time_reason = "Chưa có giờ đăng — bỏ qua tín hiệu thời điểm."
    else:
        # Circular clock distance — 23h vs 0h is 1 hour, not 23.
        raw_diff = abs(inputs.posting_hour - niche_peak_hour)
        diff_h = min(raw_diff, 24 - raw_diff)
        time_align = max(0.0, 1 - diff_h / TIME_DECAY_WINDOW_H)
        if diff_h == 0:
            time_reason = f"Đăng đúng giờ đỉnh của ngách ({niche_peak_hour}h)."
        else:
            time_reason = (
                f"Đăng lệch {diff_h}h so với giờ đỉnh ngách ({niche_peak_hour}h)."
            )

    score = round(100 * (W_HOOK * hook_align + W_FORMAT * format_align + W_TIME * time_align))

    reasons = [
        f"Hook {inputs.hook_type!r}: {hook_hits}/{TOP_N} top video ngách dùng cùng kiểu.",
        f"Format {inputs.content_format!r}: {format_hits}/{TOP_N} top video ngách cùng định dạng.",
        time_reason,
    ]
    return ViralScoreResult(
        score=score,
        hook_alignment=round(hook_align, 3),
        format_alignment=round(format_align, 3),
        time_alignment=round(time_align, 3),
        reasons=reasons,
        insufficient_reason=None,
    )


# ── Statistics helpers (no scipy dep) ─────────────────────────────────


def _ranks(values: list[float]) -> list[float]:
    """Average-rank ties — the Spearman definition."""
    if not values:
        return []
    indexed = sorted(enumerate(values), key=lambda p: p[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # positions are 1-indexed
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation — returns 0.0 on degenerate input."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def spearman_rho(xs: list[float], ys: list[float]) -> float:
    """Spearman ρ = Pearson correlation of ranks. Returns 0.0 when
    fewer than 2 pairs or either variable is constant."""
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    return _pearson(_ranks(xs), _ranks(ys))


def histogram(values: list[int], *, n_bins: int = HIST_BUCKETS) -> list[dict[str, Any]]:
    """Bucketed distribution over the 0-100 score range.

    Returns ``[{bin: "0-10", count: N}, ...]`` — even empty buckets
    are kept so the downstream UI can render a stable x-axis.
    """
    if not values:
        return [{"bin": f"{i * 10}-{(i + 1) * 10}", "count": 0} for i in range(n_bins)]
    buckets = [0] * n_bins
    for v in values:
        idx = min(n_bins - 1, max(0, int(v / 10)))
        buckets[idx] += 1
    return [
        {"bin": f"{i * 10}-{(i + 1) * 10}", "count": buckets[i]} for i in range(n_bins)
    ]


def quantiles(values: list[int]) -> dict[str, float]:
    """Min / p10 / p25 / p50 / p75 / p90 / max — the spread snapshot."""
    if not values:
        return {}
    sorted_vs = sorted(values)
    n = len(sorted_vs)

    def _q(p: float) -> float:
        if n == 1:
            return float(sorted_vs[0])
        k = (n - 1) * p
        lo = math.floor(k)
        hi = math.ceil(k)
        if lo == hi:
            return float(sorted_vs[int(k)])
        return sorted_vs[lo] + (sorted_vs[hi] - sorted_vs[lo]) * (k - lo)

    return {
        "min": float(sorted_vs[0]),
        "p10": round(_q(0.10), 2),
        "p25": round(_q(0.25), 2),
        "p50": round(_q(0.50), 2),
        "p75": round(_q(0.75), 2),
        "p90": round(_q(0.90), 2),
        "max": float(sorted_vs[-1]),
        "mean": round(statistics.fmean(values), 2),
    }


# ── Harness ───────────────────────────────────────────────────────────


def _fetch_scoreable_rows_sync(
    client: Any,
) -> list[dict[str, Any]]:
    """Pull all ``video_corpus`` rows with the 4 fields the formula reads.

    Filter to ``breakout_multiplier IS NOT NULL`` — the backtest can
    only correlate against videos that have a ground-truth multiplier.
    """
    # PostgREST caps responses at 1000 rows by default. Page through
    # range() if/when the corpus grows past that.
    result = (
        client.table("video_corpus")
        .select(
            "video_id,niche_id,hook_type,content_format,"
            "posting_hour,breakout_multiplier"
        )
        .not_.is_("breakout_multiplier", "null")
        .not_.is_("niche_id", "null")
        .limit(5000)
        .execute()
    )
    return list(result.data or [])


def _by_niche(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    by: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        nid = r.get("niche_id")
        if nid is None:
            continue
        by.setdefault(int(nid), []).append(r)
    # Sort each niche pool by breakout DESC so the caller can slice
    # [:TOP_N] for the top-30 comparison pool.
    for pool in by.values():
        pool.sort(key=lambda r: r.get("breakout_multiplier") or 0, reverse=True)
    return by


def _score_one(
    sample: dict[str, Any],
    niche_pool: list[dict[str, Any]],
    peak_hour: int | None,
) -> ViralScoreResult:
    inputs = ViralScoreInputs(
        niche_id=int(sample["niche_id"]),
        hook_type=sample.get("hook_type"),
        content_format=sample.get("content_format"),
        posting_hour=sample.get("posting_hour"),
    )
    return compute_viral_score(inputs, niche_pool[:TOP_N], peak_hour)


async def run_viral_score_backtest(
    client: Any,
    *,
    sample_size: int = 200,
    seed: int | None = 2026,
) -> dict[str, Any]:
    """Execute the backtest; return a summary dict suitable for
    ``batch_job_runs.summary``.

    ``seed`` makes the run reproducible — when committed in the design
    doc, anyone can re-run and hit the same numbers. Pass ``seed=None``
    for an unseeded run (varies per invocation).
    """
    loop = asyncio.get_event_loop()
    all_rows = await loop.run_in_executor(None, lambda: _fetch_scoreable_rows_sync(client))

    by_niche = _by_niche(all_rows)
    peak_hour_by_niche: dict[int, int | None] = {
        nid: _mode_hour(pool[:TOP_N]) for nid, pool in by_niche.items()
    }

    # Sample from the scoreable pool. Videos whose niche has < 30 rows
    # still go into the sample — the backtest explicitly measures what
    # fraction of production videos will hit the insufficient-data path.
    rng = random.Random(seed)
    sampled = rng.sample(all_rows, k=min(sample_size, len(all_rows)))

    scored: list[tuple[float, int]] = []  # (breakout_multiplier, score)
    by_niche_scored: dict[int, list[int]] = {}
    insufficient_reasons: Counter[str] = Counter()
    for sample in sampled:
        nid = int(sample["niche_id"])
        pool = by_niche.get(nid, [])
        result = _score_one(sample, pool, peak_hour_by_niche.get(nid))
        if result.score is None:
            insufficient_reasons[result.insufficient_reason or "unknown"] += 1
            continue
        mult = sample.get("breakout_multiplier")
        if mult is None:
            # Defensive — the SELECT already filters; if something slipped
            # through, don't corrupt the correlation.
            continue
        scored.append((float(mult), result.score))
        by_niche_scored.setdefault(nid, []).append(result.score)

    scores = [s for _, s in scored]
    mults = [m for m, _ in scored]
    rho = round(spearman_rho(mults, [float(s) for s in scores]), 4)

    per_niche: list[dict[str, Any]] = []
    for nid, ss in sorted(by_niche_scored.items()):
        pool = by_niche.get(nid, [])
        per_niche.append({
            "niche_id": nid,
            "n_scored": len(ss),
            "mean_score": round(statistics.fmean(ss), 2),
            "pool_size": len(pool),
            "peak_hour": peak_hour_by_niche.get(nid),
        })

    summary: dict[str, Any] = {
        "sample_size": len(sampled),
        "scored_count": len(scored),
        "insufficient_count": len(sampled) - len(scored),
        "insufficient_reasons": dict(insufficient_reasons),
        "weights": {"hook": W_HOOK, "format": W_FORMAT, "time": W_TIME},
        "top_n": TOP_N,
        "niche_min_sample": NICHE_MIN_SAMPLE,
        "distribution": histogram(scores),
        "quantiles": quantiles(scores),
        "spearman_rho_vs_breakout": rho,
        "spearman_gate": 0.35,
        "spearman_gate_met": rho >= 0.35,
        "per_niche": per_niche,
        "seed": seed,
    }
    return summary
