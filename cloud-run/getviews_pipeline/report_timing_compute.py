"""Phase C.4.2 — deterministic aggregators for Timing reports.

Data sources:
- ``video_corpus.posted_at`` (or ``created_at`` fallback) → day × hour_bucket
  cell ids for the 7×8 heatmap.
- ``video_corpus.views`` → per-cell median vs niche median → lift multiplier
  (driven through ``classify_variance`` to set the ``VarianceNote`` chip).
- ``timing_top_window_streak(p_niche_id, p_day, p_hour_bucket)`` RPC →
  streak length for the #1 window's fatigue band.

Contracts:
- Grid values normalised 0–10 so the UI tone ramp (5 levels) maps cleanly.
- ``compute_top_windows`` returns internal ``day_idx`` / ``hour_idx`` keys
  so the report builder can feed them straight into the streak RPC without
  re-parsing Vietnamese labels.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_types import ActionCardPayload
from getviews_pipeline.report_timing import (  # noqa: F401 — circular-safe (runtime only)
    DAY_LABELS_VN,  # unused here but re-exported for callers
    HOUR_BUCKETS_VN,
    _day_vn,
    _hours_vn,
)

logger = logging.getLogger(__name__)


# ── Heatmap build + top-window ranking ─────────────────────────────────────


_HOUR_BUCKET_EDGES = [6, 9, 12, 15, 18, 20, 22, 24]  # + wrap to 0–3


def _bucket_for_hour(hour: int) -> int:
    """Map a 24h hour into one of the 8 buckets used by the heatmap.

    Buckets: 6–9, 9–12, 12–15, 15–18, 18–20, 20–22, 22–24, 0–3. Hours 3–6
    (deep sleep) fold into the last bucket to match the reference UI which
    doesn't expose a 3–6 slot.
    """
    h = hour % 24
    if h < 6:
        return 7  # 0–3 / sleep
    if h < 9:
        return 0
    if h < 12:
        return 1
    if h < 15:
        return 2
    if h < 18:
        return 3
    if h < 20:
        return 4
    if h < 22:
        return 5
    return 6  # 22–24


def _parse_posted_at(row: dict[str, Any]) -> datetime | None:
    raw = row.get("posted_at") or row.get("indexed_at") or row.get("created_at")
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


def build_heatmap_grid(
    corpus_rows: list[dict[str, Any]],
) -> tuple[list[list[float]], list[list[int]], float]:
    """Return ``(grid, counts, niche_median_views)``.

    - ``grid[7][8]`` — values 0–10. Each cell is the per-cell views median
      mapped to a 0–10 scale where 10 = the top cell across the grid.
    - ``counts[7][8]`` — number of videos falling into each cell. Used
      by ``classify_variance`` for the sparse-sample chip.
    - ``niche_median_views`` — global median across all rows, needed for
      the lift multiplier on ``top_window``.
    """
    # Python's weekday(): Monday=0, Sunday=6. Matches the reference (T2..CN).
    buckets: list[list[list[float]]] = [[[] for _ in range(8)] for _ in range(7)]
    for row in corpus_rows:
        dt = _parse_posted_at(row)
        if not dt:
            continue
        try:
            views = float(row.get("views") or 0)
        except Exception:
            continue
        if views <= 0:
            continue
        day_idx = dt.weekday()
        hour_idx = _bucket_for_hour(dt.hour)
        buckets[day_idx][hour_idx].append(views)

    medians: list[list[float]] = [[_median(cell) for cell in row] for row in buckets]
    counts: list[list[int]] = [[len(cell) for cell in row] for row in buckets]

    # Normalize to 0–10 against the max cell median.
    flat = [v for row in medians for v in row if v > 0]
    peak = max(flat) if flat else 0.0
    grid: list[list[float]] = [
        [round(10.0 * v / peak, 1) if peak > 0 else 0.0 for v in row] for row in medians
    ]

    all_views = [float(row.get("views") or 0) for row in corpus_rows if float(row.get("views") or 0) > 0]
    niche_median = _median(all_views)
    return grid, counts, niche_median


def compute_top_windows(
    grid: list[list[float]],
    counts: list[list[int]],
    *,
    niche_median: float,
) -> list[dict[str, Any]]:
    """Rank the top windows across the grid. Returns at most 5 entries with
    both label and index fields so callers can feed ``day_idx``/``hour_idx``
    into the streak RPC without re-parsing labels.

    Lift multiplier = (peak-scaled value / 5.0). Cells with < 2 samples are
    dropped to avoid spurious single-video wins.
    """
    candidates: list[dict[str, Any]] = []
    for di, row in enumerate(grid):
        for hi, v in enumerate(row):
            if v <= 0:
                continue
            if counts[di][hi] < 2:
                continue
            # Lift against niche_median is represented by the normalised score.
            # v == 10 → strongest cell ≈ top performer; treat 5.0 as parity.
            lift = max(1.0, v / 5.0)
            candidates.append(
                {
                    "day_idx": di,
                    "hour_idx": hi,
                    "day": _day_vn(di),
                    "hours": _hours_vn(hi),
                    "value": v,
                    "sample": counts[di][hi],
                    "lift_multiplier": round(lift, 2),
                }
            )
    candidates.sort(key=lambda x: x["value"], reverse=True)
    # Deduplicate day/hours pairs defensively.
    seen: set[tuple[int, int]] = set()
    dedup: list[dict[str, Any]] = []
    for c in candidates:
        key = (c["day_idx"], c["hour_idx"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)
        if len(dedup) >= 5:
            break
    return dedup


# ── Variance classification — prevents false confidence on thin heatmaps ───


def classify_variance(top_windows: list[dict[str, Any]]) -> dict[str, str]:
    """Map the #1 window's lift to one of ``strong | weak | sparse``.

    - ``strong`` (lift ≥ 2.0)   → "Heatmap CÓ ý nghĩa" — ship the heatmap.
    - ``weak``   (1.3 ≤ lift)   → "Heatmap có xu hướng nhưng chưa rõ" — show
      with a cautionary note.
    - ``sparse`` (lift < 1.3)   → "Heatmap CHƯA ổn định — mẫu thưa" — UI
      falls back to top-3 windows list only.
    """
    if not top_windows:
        return {
            "kind": "sparse",
            "label": "Heatmap CHƯA ổn định — mẫu thưa",
            "detail": "Chưa đủ video để xếp hạng cửa sổ post.",
        }
    lift = float(top_windows[0].get("lift_multiplier") or 1.0)
    if lift >= 2.0:
        return {
            "kind": "strong",
            "label": "Heatmap CÓ ý nghĩa",
            "detail": f"Cửa sổ mạnh nhất gấp {lift:.1f}× median — tín hiệu ổn định.",
        }
    if lift >= 1.3:
        return {
            "kind": "weak",
            "label": "Heatmap có xu hướng nhưng chưa rõ",
            "detail": f"Cửa sổ mạnh nhất gấp {lift:.1f}× median — còn biên độ cải thiện.",
        }
    return {
        "kind": "sparse",
        "label": "Heatmap CHƯA ổn định — mẫu thưa",
        "detail": f"Cửa sổ mạnh nhất chỉ {lift:.1f}× median — dùng top-3 để định hướng.",
    }


# ── Top-window streak (timing_top_window_streak RPC) ───────────────────────


def fetch_top_window_streak(sb: Any, niche_id: int, day: int, hour_bucket: int) -> int:
    """Return consecutive weeks at #1 for ``(day, hour_bucket)``.

    The 20260430000002 migration currently returns 0 (stub); the helper
    fails open so an RPC error never blocks the report. When the RPC body
    lands (Phase D) the fatigue band lights up automatically.
    """
    try:
        res = sb.rpc(
            "timing_top_window_streak",
            {"p_niche_id": niche_id, "p_day": day, "p_hour_bucket": hour_bucket},
        ).execute()
        raw = res.data
        if raw is None:
            return 0
        if isinstance(raw, int):
            return max(0, raw)
        if isinstance(raw, list) and raw:
            first = raw[0]
            if isinstance(first, dict):
                return int(first.get("timing_top_window_streak") or 0)
            return int(first or 0)
        return 0
    except Exception as exc:
        logger.warning("[timing] top_window_streak RPC skipped: %s", exc)
        return 0


# ── Action cards ───────────────────────────────────────────────────────────


def static_timing_action_cards(top_window: dict[str, Any] | None) -> list[ActionCardPayload]:
    """Two CTAs keyed to the #1 window. Forecast uses lift multiplier for the
    primary card so the user sees the concrete expected uplift."""
    lift = float((top_window or {}).get("lift_multiplier") or 1.0)
    day = str((top_window or {}).get("day") or "—")
    hours = str((top_window or {}).get("hours") or "—")
    lift_str = f"{lift:.1f}× median" if lift > 1.0 else "≈ median"
    return [
        ActionCardPayload(
            icon="calendar",
            title=f"Lên lịch post vào {day} {hours}",
            sub="Schedule video tiếp theo vào cửa sổ mạnh nhất",
            cta="Mở lịch",
            primary=True,
            route="/app/script",
            forecast={"expected_range": lift_str, "baseline": "1.0× median"},
        ),
        ActionCardPayload(
            icon="search",
            title="Xem kênh đối thủ khai thác cửa sổ này",
            sub=f"Ai đang post mạnh trong {day} {hours}",
            cta="Mở",
            route="/app/kol",
            forecast={"expected_range": "—", "baseline": "—"},
        ),
    ]


# ── DB loader ──────────────────────────────────────────────────────────────


def load_timing_inputs(sb: Any, niche_id: int, window_days: int) -> dict[str, Any] | None:
    """Load niche label + corpus slice within the window. Uses a wider 14-day
    floor than Pattern/Ideas so sparse niches still surface a top-3 list."""
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

        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(window_days, 14))).isoformat()
        cres = (
            sb.table("video_corpus")
            .select("video_id, views, posted_at, indexed_at, created_at")
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff)
            .order("indexed_at", desc=True)
            .limit(2500)
            .execute()
        )
        corpus = list(cres.data or [])
        return {"niche_label": label, "corpus": corpus}
    except Exception as exc:
        logger.warning("[timing] load_timing_inputs failed: %s", exc)
        return None
