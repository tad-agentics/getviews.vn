"""Deterministic aggregators for Lifecycle reports.

Format mode is the only mode that aggregates live corpus today — we have
``video_corpus.content_format`` (the 15-value taxonomy locked by
``corpus_ingest.classify_format``) and ``views`` + ``indexed_at`` which
together give us enough to compute per-format reach deltas and stages.

Hook-fatigue and subniche modes still ship fixture cells from
``report_lifecycle.build_fixture_lifecycle_report`` because the required
signal isn't available in the corpus schema yet:

- Hook fatigue needs per-hook weekly reach tracking. The corpus has a
  ``hook_type`` field but it isn't bucketed into a fatigue timeseries;
  the Layer-0 migration dashboard owns that computation and hasn't been
  wired into Answer sessions.
- Subniche needs a stable sub-niche taxonomy per niche. The current
  ``niche_id`` is flat — a subniche column was scoped out of the
  2026-04-22 audit. When it lands we swap fixture cells for real
  aggregation here without changing the report shape.

Both paths still get query-aware Vietnamese narrative from
``report_lifecycle_gemini`` so the output isn't identical across
follow-ups.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Human-readable labels for the 15-value content_format taxonomy. Missing
# rows get the raw enum as a last-resort label.
_FORMAT_LABELS_VN: dict[str, str] = {
    "mukbang": "Mukbang / ASMR ăn uống",
    "grwm": "GRWM / morning routine",
    "recipe": "Recipe / công thức nấu",
    "haul": "Unboxing / haul",
    "review": "Product review",
    "tutorial": "Tutorial / hướng dẫn",
    "comparison": "So sánh / versus",
    "storytelling": "Storytelling",
    "before_after": "Trước/sau (before/after)",
    "pov": "POV",
    "outfit_transition": "Outfit / transition",
    "vlog": "Vlog",
    "dance": "Dance",
    "faceless": "Faceless",
    "other": "Khác",
}

# Minimum sample count per format before we include it in the cell list.
# Below this the per-format median is too noisy to classify a stage on.
_FORMAT_MIN_SAMPLES = 5

# Lifecycle sample floor — matches the timing / pattern thin-corpus gate.
LIFECYCLE_SAMPLE_FLOOR = 80


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def _stage_for_delta(delta_pct: float) -> str:
    """Map reach-delta-% → lifecycle stage.

    Thresholds kept conservative so a single noisy week doesn't flip a
    format from peak to declining. Tuned against the fixture cells so a
    fresh format shows up as ``rising``, a solid established format as
    ``peak``, a maturing format as ``plateau``, and a sliding format as
    ``declining``.
    """
    if delta_pct >= 15.0:
        return "rising"
    if delta_pct >= 5.0:
        return "peak"
    if delta_pct >= -5.0:
        return "plateau"
    return "declining"


def _health_score_for(delta_pct: float, lift_vs_median: float) -> int:
    """Health 0-100 that combines growth (reach delta) and absolute level
    (lift vs niche median). A declining format with still-high lift reads
    as "weakening but useful"; a rising format with low lift reads as
    "new but unproven".
    """
    # Base: 50 at delta=0, swing ±40 for ±30% delta.
    base = 50 + max(-40, min(40, delta_pct * 1.33))
    # Bonus: +10 at lift 2×, −10 at lift 0.5×.
    bonus = max(-10, min(10, (lift_vs_median - 1.0) * 10))
    return max(0, min(100, int(round(base + bonus))))


def _split_by_window(
    rows: list[dict[str, Any]],
    *,
    recent_cutoff: datetime,
    window_start: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (recent, prior) rows split by ``recent_cutoff``.

    Both halves are inside ``[window_start, now]`` so the per-format
    median is comparable across them."""
    recent: list[dict[str, Any]] = []
    prior: list[dict[str, Any]] = []
    for r in rows:
        ts = _parse_ts(r.get("indexed_at") or r.get("created_at") or r.get("posted_at"))
        if ts is None or ts < window_start:
            continue
        if ts >= recent_cutoff:
            recent.append(r)
        else:
            prior.append(r)
    return recent, prior


def compute_format_cells(
    corpus_rows: list[dict[str, Any]],
    *,
    window_days: int = 30,
) -> list[dict[str, Any]]:
    """Aggregate corpus by ``content_format`` → ranked LifecycleCell dicts.

    Compares the most recent ``window_days // 2`` days against the prior
    ``window_days // 2`` days so the ``reach_delta_pct`` is a real
    week-over-week change, not a vs-niche-median snapshot. Formats with
    fewer than ``_FORMAT_MIN_SAMPLES`` rows in either half are dropped.

    Returns a list ordered by health_score DESC so the first cell is the
    "dẫn đầu" one the subject line quotes.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    split_at = now - timedelta(days=max(window_days // 2, 7))

    recent, prior = _split_by_window(
        corpus_rows,
        recent_cutoff=split_at,
        window_start=window_start,
    )

    # Global median for lift vs niche.
    all_views = [
        float(r.get("views") or 0)
        for r in corpus_rows
        if float(r.get("views") or 0) > 0
    ]
    niche_median = _median(all_views) or 1.0

    # Bucket views by (format, window-half).
    recent_by_fmt: dict[str, list[float]] = {}
    prior_by_fmt: dict[str, list[float]] = {}
    for row in recent:
        fmt = str(row.get("content_format") or "other")
        v = float(row.get("views") or 0)
        if v > 0:
            recent_by_fmt.setdefault(fmt, []).append(v)
    for row in prior:
        fmt = str(row.get("content_format") or "other")
        v = float(row.get("views") or 0)
        if v > 0:
            prior_by_fmt.setdefault(fmt, []).append(v)

    cells: list[dict[str, Any]] = []
    for fmt in set(recent_by_fmt) | set(prior_by_fmt):
        rs = recent_by_fmt.get(fmt, [])
        ps = prior_by_fmt.get(fmt, [])
        if len(rs) < _FORMAT_MIN_SAMPLES or len(ps) < _FORMAT_MIN_SAMPLES:
            continue
        rm = _median(rs)
        pm = _median(ps)
        if pm <= 0:
            continue
        delta = (rm - pm) / pm * 100.0
        lift = rm / niche_median if niche_median > 0 else 1.0
        cells.append(
            {
                "name": _FORMAT_LABELS_VN.get(fmt, fmt.replace("_", " ").title()),
                "stage": _stage_for_delta(delta),
                "reach_delta_pct": round(delta, 1),
                "health_score": _health_score_for(delta, lift),
                # Retention is not tracked per-format in the corpus —
                # leave None so the UI doesn't render a misleading value.
                "retention_pct": None,
                "instance_count": None,
                "insight": "",  # filled by report_lifecycle_gemini
                # Internal — stripped before Pydantic validation.
                "_recent_count": len(rs),
                "_prior_count": len(ps),
            }
        )

    # Rank by health_score DESC so the lead cell drives the subject line.
    cells.sort(key=lambda c: c["health_score"], reverse=True)
    # Clamp cells to the Pydantic max of 12 — aggregation on a 15-value
    # taxonomy shouldn't exceed that, but keep the guard.
    return cells[:12]


def strip_internal_fields(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop ``_recent_count`` / ``_prior_count`` before Pydantic validation."""
    out: list[dict[str, Any]] = []
    for c in cells:
        out.append({k: v for k, v in c.items() if not k.startswith("_")})
    return out


def load_lifecycle_inputs(
    sb: Any,
    niche_id: int,
    window_days: int,
) -> dict[str, Any] | None:
    """Fetch niche label + the corpus slice used by ``compute_format_cells``.

    Mirrors ``load_timing_inputs`` — same 14-day floor, same indexed_at
    filter, same ``select()`` narrow to keep the payload small.
    """
    try:
        nt = (
            sb.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .maybe_single()
            .execute()
        )
        row = nt.data or {}
        label = str(row.get("name_vn") or row.get("name_en") or f"Niche {niche_id}")

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=max(window_days, 14))
        ).isoformat()
        cres = (
            sb.table("video_corpus")
            .select(
                "video_id, views, content_format, indexed_at, created_at, posted_at"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff)
            .order("indexed_at", desc=True)
            .limit(2500)
            .execute()
        )
        corpus = list(cres.data or [])
        return {"niche_label": label, "corpus": corpus}
    except Exception as exc:
        logger.warning("[lifecycle] load_lifecycle_inputs failed: %s", exc)
        return None
