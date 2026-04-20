"""Phase C.4 — Timing report aggregator (fixture + live pipeline + fatigue).

Design source: ``artifacts/uiux-reference/screens/thread-turns.jsx`` lines
88–192. New §J sections over the reference:

- ``variance_note`` — chip keyed to ``top_window.lift_multiplier`` (strong /
  weak / sparse) so weak heatmaps don't ship false confidence.
- ``fatigue_band`` — populated when ``timing_top_window_streak`` RPC reports
  4+ consecutive weeks at #1 for the same (day, hour_bucket).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    SourceRow,
    TimingPayload,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)

# ── Shared labels (Vietnamese UI copy bound in the payload, not client-side) ─

DAY_LABELS_VN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
HOUR_BUCKETS_VN = ["6–9", "9–12", "12–15", "15–18", "18–20", "20–22", "22–24", "0–3"]


def _day_vn(idx: int) -> str:
    labels = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    return labels[idx % 7]


def _hours_vn(idx: int) -> str:
    return HOUR_BUCKETS_VN[idx % 8]


# ── Fixture path (C.1.2) ────────────────────────────────────────────────────


def build_fixture_timing_report() -> dict[str, Any]:
    """Full-sample fixture — 72-video corpus, strong variance (lift > 2×)."""
    grid: list[list[float]] = [
        [1.0, 3.0, 4.0, 5.0, 8.0, 9.0, 6.0, 2.0],
        [1.0, 2.0, 4.0, 5.0, 9.0, 10.0, 7.0, 2.0],
        [1.0, 3.0, 5.0, 6.0, 8.0, 9.0, 7.0, 3.0],
        [2.0, 3.0, 4.0, 6.0, 9.0, 10.0, 8.0, 3.0],
        [2.0, 3.0, 5.0, 7.0, 9.0, 10.0, 8.0, 4.0],
        [3.0, 5.0, 7.0, 8.0, 10.0, 9.0, 7.0, 5.0],
        [4.0, 6.0, 7.0, 8.0, 9.0, 7.0, 5.0, 4.0],
    ]
    payload = TimingPayload(
        confidence=ConfidenceStrip(
            sample_size=112,
            window_days=14,
            niche_scope="Tech",
            freshness_hours=3,
            intent_confidence="high",
        ),
        top_window={
            "day": "Thứ 7",
            "hours": "18–22",
            "lift_multiplier": 2.8,
            "insight": (
                "Post trong cửa sổ này được view gấp 2.8× trung bình ngách; "
                "lowest: 3–6h sáng Thứ 2."
            ),
        },
        top_3_windows=[
            {"rank": 1, "day": "Thứ 7", "hours": "18–20", "lift_multiplier": 2.8},
            {"rank": 2, "day": "Thứ 6", "hours": "20–22", "lift_multiplier": 2.5},
            {"rank": 3, "day": "Thứ 5", "hours": "20–22", "lift_multiplier": 2.3},
        ],
        lowest_window={"day": "Thứ 2", "hours": "0–3"},
        grid=grid,
        variance_note={
            "kind": "strong",
            "label": "Heatmap CÓ ý nghĩa",
            "detail": "Cửa sổ mạnh nhất gấp 2.8× trung bình — tín hiệu ổn định.",
        },
        fatigue_band=None,
        actions=[
            ActionCardPayload(
                icon="calendar",
                title="Lên lịch post thử vào T7 18:00",
                sub="Schedule video tiếp theo vào cửa sổ mạnh nhất",
                cta="Mở lịch",
                primary=True,
                route="/app/script",
                forecast={"expected_range": "2.8× median", "baseline": "1.0× median"},
            ),
            ActionCardPayload(
                icon="search",
                title="Xem kênh đối thủ khai thác cửa sổ này",
                sub="Ai đang post mạnh trong khung T7 18–22",
                cta="Mở",
                route="/app/kol",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ],
        sources=[SourceRow(kind="video", label="Corpus", count=112, sub="Tech · 14d")],
        related_questions=[
            "Cửa sổ này giữ #1 được bao lâu rồi?",
            "Khung mạnh cho ngách con Tech/AI?",
            "Cửa sổ khác cho creator < 10K follower?",
        ],
    )
    return payload.model_dump()


ANSWER_FIXTURE_TIMING: dict[str, Any] = validate_and_store_report(
    "timing",
    build_fixture_timing_report(),
)


def build_thin_corpus_timing_report() -> dict[str, Any]:
    """Empty-state: ``sample_size < 80`` → hide cells < 5 + show only top-3 list.

    The body component honours this shape by reading ``variance_note.kind ==
    "sparse"`` and masking grid cells below the floor before render.
    """
    inner = build_fixture_timing_report()
    conf = inner["confidence"]
    if isinstance(conf, dict):
        conf["sample_size"] = 42
    inner["variance_note"] = {
        "kind": "sparse",
        "label": "Heatmap CHƯA ổn định — mẫu thưa",
        "detail": "Chỉ 42 video trong 14 ngày qua; chỉ đọc top-3 cửa sổ.",
    }
    inner["top_window"]["insight"] = (
        "Mẫu nhỏ: dùng 3 cửa sổ bên phải để định hướng, "
        "không kết luận toàn ngách."
    )
    return inner


def build_fatigued_timing_report() -> dict[str, Any]:
    """Active fatigue band — top window has been #1 for 6 straight weeks."""
    inner = build_fixture_timing_report()
    inner["fatigue_band"] = {
        "weeks_at_top": 6,
        "copy": (
            "Cửa sổ T7 18–22 đã là #1 trong 6 tuần liên tiếp — có thể đang "
            "bão hòa; thử test thêm một cửa sổ phụ tuần tới."
        ),
    }
    return inner


# ── Live pipeline (C.4.2) ──────────────────────────────────────────────────


def build_timing_report(
    niche_id: int,
    query: str,  # noqa: ARG001 — reserved for future niche refinement
    window_days: int = 14,
) -> dict[str, Any]:
    """Live Timing report. Falls back to fixture when DB / niche is unavailable.

    Empty state (``sample_size < 80``) → thin-corpus fixture (variance kind
    "sparse"). Fatigue band populated when ``timing_top_window_streak`` RPC
    returns ≥ 4 for the chosen top (day, hour_bucket) pair.
    """
    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[timing] service client unavailable: %s — fixture path", exc)
        data = build_fixture_timing_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        return data

    from getviews_pipeline.report_timing_compute import (
        build_heatmap_grid,
        classify_variance,
        compute_top_windows,
        fetch_top_window_streak,
        load_timing_inputs,
        static_timing_action_cards,
    )

    ctx = load_timing_inputs(sb, niche_id, window_days)
    if ctx is None:
        data = build_fixture_timing_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        return data

    corpus: list[dict[str, Any]] = ctx["corpus"]
    niche_label = str(ctx["niche_label"])
    sample_n = len(corpus)

    if niche_id <= 0 or sample_n < 80:
        thin = build_thin_corpus_timing_report()
        if isinstance(thin.get("confidence"), dict):
            thin["confidence"]["window_days"] = window_days
            thin["confidence"]["niche_scope"] = niche_label
            thin["confidence"]["sample_size"] = sample_n
        return thin

    grid, counts, niche_median = build_heatmap_grid(corpus)
    top_windows = compute_top_windows(grid, counts, niche_median=niche_median)
    lowest = _lowest_window_from_grid(grid)
    variance = classify_variance(top_windows)

    # Fatigue: only populate when the #1 window has been top for 4+ weeks.
    fatigue: dict[str, Any] | None = None
    if top_windows:
        top = top_windows[0]
        streak = fetch_top_window_streak(sb, niche_id, top["day_idx"], top["hour_idx"])
        if streak >= 4:
            fatigue = {
                "weeks_at_top": streak,
                "copy": (
                    f"Cửa sổ {top['day']} {top['hours']} đã là #1 trong "
                    f"{streak} tuần liên tiếp — có thể đang bão hòa; thử "
                    f"test thêm một cửa sổ phụ tuần tới."
                ),
            }

    lift = top_windows[0]["lift_multiplier"] if top_windows else 1.0
    insight = (
        f"Post trong cửa sổ {top_windows[0]['day']} {top_windows[0]['hours']} "
        f"được view gấp {lift:.1f}× trung bình ngách {niche_label}. "
        f"Thấp nhất: {lowest['hours']} {lowest['day']}."
    ) if top_windows else "Chưa đủ tín hiệu để xếp hạng cửa sổ."

    payload = TimingPayload(
        confidence=ConfidenceStrip(
            sample_size=sample_n,
            window_days=window_days,
            niche_scope=niche_label,
            freshness_hours=_freshness_from_corpus(corpus),
            intent_confidence="high" if sample_n >= 150 else "medium",
        ),
        top_window=(
            {
                "day": top_windows[0]["day"],
                "hours": top_windows[0]["hours"],
                "lift_multiplier": lift,
                "insight": insight,
            }
            if top_windows
            else {"day": "—", "hours": "—", "lift_multiplier": 1.0, "insight": insight}
        ),
        top_3_windows=[
            {
                "rank": i + 1,
                "day": w["day"],
                "hours": w["hours"],
                "lift_multiplier": w["lift_multiplier"],
            }
            for i, w in enumerate(top_windows[:3])
        ],
        lowest_window=lowest,
        grid=grid,
        variance_note=variance,
        fatigue_band=fatigue,
        actions=static_timing_action_cards(top_windows[0] if top_windows else None),
        sources=[SourceRow(kind="video", label="Corpus", count=sample_n, sub=f"{niche_label} · {window_days}d")],
        related_questions=[
            f"Cửa sổ này giữ #1 được bao lâu trong {niche_label}?",
            "Có cửa sổ phụ cho kênh nhỏ?",
            "Đổi khung giờ theo ngách con?",
        ],
    )
    return payload.model_dump()


def _lowest_window_from_grid(grid: list[list[float]]) -> dict[str, str]:
    if not grid or not grid[0]:
        return {"day": "—", "hours": "—"}
    lowest_val = float("inf")
    lowest: tuple[int, int] | None = None
    for di, row in enumerate(grid):
        for hi, v in enumerate(row):
            if v < lowest_val:
                lowest_val = v
                lowest = (di, hi)
    if lowest is None:
        return {"day": "—", "hours": "—"}
    return {"day": _day_vn(lowest[0]), "hours": _hours_vn(lowest[1])}


def _freshness_from_corpus(corpus: list[dict[str, Any]]) -> int:
    best: datetime | None = None
    for row in corpus:
        raw = row.get("indexed_at") or row.get("created_at") or row.get("posted_at")
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if best is None or d > best:
            best = d
    if best is None:
        return 24
    delta = datetime.now(timezone.utc) - best.astimezone(timezone.utc)
    return max(1, int(delta.total_seconds() // 3600))
