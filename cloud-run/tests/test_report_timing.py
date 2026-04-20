"""Phase C.4 — Timing report tests.

Coverage:
- Fixtures validate against §J `TimingPayload` (full / thin / fatigued).
- `build_timing_report` entry: service-client unavailable → fixture fallback;
  thin niche → thin fixture; full corpus → variance classified strong/weak.
- `build_heatmap_grid` normalises 0–10 against the peak cell.
- `compute_top_windows` drops < 2-sample cells + caps at 5 + dedupes.
- `classify_variance` maps lift thresholds to strong / weak / sparse.
- `fetch_top_window_streak` fails open when the RPC raises.
- `_bucket_for_hour` covers all 24 hours (incl. 3–6 wraps to 0–3 bucket).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_timing import (
    build_fatigued_timing_report,
    build_fixture_timing_report,
    build_thin_corpus_timing_report,
    build_timing_report,
)
from getviews_pipeline.report_timing_compute import (
    _bucket_for_hour,
    build_heatmap_grid,
    classify_variance,
    compute_top_windows,
    fetch_top_window_streak,
    static_timing_action_cards,
)
from getviews_pipeline.report_types import TimingPayload, validate_and_store_report


# ── Fixture / thin / fatigued envelope validation ──────────────────────────


def test_fixture_timing_validates() -> None:
    inner = build_fixture_timing_report()
    p = TimingPayload.model_validate(inner)
    assert p.confidence.sample_size >= 80
    assert len(p.grid) == 7 and all(len(row) == 8 for row in p.grid)
    assert len(p.top_3_windows) == 3
    assert p.variance_note["kind"] == "strong"
    assert p.fatigue_band is None


def test_fixture_envelope_validates() -> None:
    inner = build_fixture_timing_report()
    env = validate_and_store_report("timing", inner)
    assert env["kind"] == "timing"
    assert "report" in env


def test_thin_corpus_sets_sparse_variance() -> None:
    inner = build_thin_corpus_timing_report()
    p = TimingPayload.model_validate(inner)
    assert p.confidence.sample_size < 80
    assert p.variance_note["kind"] == "sparse"


def test_fatigued_fixture_populates_fatigue_band() -> None:
    inner = build_fatigued_timing_report()
    p = TimingPayload.model_validate(inner)
    assert p.fatigue_band is not None
    assert p.fatigue_band["weeks_at_top"] >= 4


# ── build_timing_report — live entry fallback paths ────────────────────────


def test_build_timing_report_threads_window_days_on_fixture_fallback() -> None:
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_timing_report(1, "giờ nào post tốt?", window_days=21)
    p = TimingPayload.model_validate(inner)
    assert p.confidence.window_days == 21


@patch("getviews_pipeline.report_timing_compute.load_timing_inputs")
def test_build_timing_report_thin_niche_routes_to_thin(mock_load: MagicMock) -> None:
    mock_load.return_value = {"niche_label": "Tech", "corpus": []}
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_timing_report(5, "q", window_days=14)
    p = TimingPayload.model_validate(inner)
    assert p.confidence.sample_size < 80
    assert p.variance_note["kind"] == "sparse"


@patch("getviews_pipeline.report_timing_compute.fetch_top_window_streak")
@patch("getviews_pipeline.report_timing_compute.load_timing_inputs")
def test_build_timing_report_full_corpus_returns_strong_variance(
    mock_load: MagicMock, mock_streak: MagicMock
) -> None:
    # Synthesise 100 rows concentrated on Saturday 18–20 (day_idx=5, hour_idx=4).
    base = datetime(2026, 4, 18, 19, 0, tzinfo=timezone.utc)  # Saturday 19:00 UTC
    rows: list[dict[str, object]] = []
    # Strong cell: 60 rows, 20000 views each.
    for i in range(60):
        rows.append({"video_id": f"s{i}", "views": 20_000, "posted_at": base.isoformat()})
    # Weak cells: 40 rows spread across other buckets.
    for i in range(40):
        off = timedelta(days=(i % 6) + 1, hours=(i % 4) + 1)
        rows.append(
            {
                "video_id": f"w{i}",
                "views": 3_000,
                "posted_at": (base + off).isoformat(),
            }
        )
    mock_load.return_value = {"niche_label": "Tech", "corpus": rows}
    mock_streak.return_value = 0
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_timing_report(5, "q", window_days=14)
    p = TimingPayload.model_validate(inner)
    assert p.confidence.sample_size == 100
    assert p.variance_note["kind"] == "strong"
    # Top window should snap to Saturday (Thứ 7) 18–20.
    assert p.top_windows["day"] if hasattr(p, "top_windows") else True  # sanity
    assert p.top_window["day"] == "Thứ 7"
    assert p.top_window["hours"] == "18–20"
    assert p.fatigue_band is None  # streak returned 0


@patch("getviews_pipeline.report_timing_compute.fetch_top_window_streak", return_value=6)
@patch("getviews_pipeline.report_timing_compute.load_timing_inputs")
def test_build_timing_report_populates_fatigue_when_streak_geq_4(
    mock_load: MagicMock, _streak: MagicMock
) -> None:
    base = datetime(2026, 4, 18, 19, 0, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    for i in range(100):
        off = timedelta(minutes=i * 7)
        rows.append({"video_id": f"v{i}", "views": 15_000, "posted_at": (base + off).isoformat()})
    mock_load.return_value = {"niche_label": "Tech", "corpus": rows}
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_timing_report(5, "q", window_days=14)
    p = TimingPayload.model_validate(inner)
    assert p.fatigue_band is not None
    assert p.fatigue_band["weeks_at_top"] == 6


# ── Compute helpers ───────────────────────────────────────────────────────


def test_bucket_for_hour_maps_all_24_hours_to_8_slots() -> None:
    seen: set[int] = set()
    for h in range(24):
        b = _bucket_for_hour(h)
        assert 0 <= b <= 7
        seen.add(b)
    # Expect all 8 buckets reachable.
    assert seen == set(range(8))


def test_bucket_for_hour_wraps_3_to_6_into_sleep_slot() -> None:
    # 3h, 4h, 5h → bucket 7 (0–3 / sleep). 6h → bucket 0.
    assert _bucket_for_hour(3) == 7
    assert _bucket_for_hour(5) == 7
    assert _bucket_for_hour(6) == 0


def test_build_heatmap_grid_normalises_to_0_10() -> None:
    base = datetime(2026, 4, 18, 19, 0, tzinfo=timezone.utc)
    rows = [
        {"views": 10_000, "posted_at": base.isoformat()},
        {"views": 10_000, "posted_at": base.isoformat()},
        {"views": 2_000, "posted_at": (base + timedelta(days=1)).isoformat()},
        {"views": 2_000, "posted_at": (base + timedelta(days=1)).isoformat()},
    ]
    grid, counts, niche_median = build_heatmap_grid(rows)
    assert len(grid) == 7 and len(grid[0]) == 8
    # Saturday 18–20 cell is the peak (value normalises to 10).
    assert grid[5][4] == 10.0
    assert counts[5][4] == 2
    assert niche_median > 0


def test_compute_top_windows_drops_single_sample_cells() -> None:
    grid = [[0.0] * 8 for _ in range(7)]
    counts = [[0] * 8 for _ in range(7)]
    # A single-sample 10 should be dropped.
    grid[5][4] = 10.0
    counts[5][4] = 1
    # A 2-sample 8 should appear.
    grid[4][5] = 8.0
    counts[4][5] = 2
    ranked = compute_top_windows(grid, counts, niche_median=5000.0)
    assert len(ranked) == 1
    assert ranked[0]["day"] == "Thứ 6" and ranked[0]["hours"] == "20–22"


def test_compute_top_windows_caps_at_5() -> None:
    grid = [[float(i + j + 1) for j in range(8)] for i in range(7)]
    counts = [[5] * 8 for _ in range(7)]
    ranked = compute_top_windows(grid, counts, niche_median=5000.0)
    assert len(ranked) == 5


def test_classify_variance_thresholds() -> None:
    strong = classify_variance([{"lift_multiplier": 2.5}])
    assert strong["kind"] == "strong"
    weak = classify_variance([{"lift_multiplier": 1.5}])
    assert weak["kind"] == "weak"
    sparse = classify_variance([{"lift_multiplier": 1.05}])
    assert sparse["kind"] == "sparse"
    empty = classify_variance([])
    assert empty["kind"] == "sparse"


def test_fetch_top_window_streak_fails_open_on_rpc_error() -> None:
    sb = MagicMock()
    sb.rpc.side_effect = RuntimeError("rpc failed")
    assert fetch_top_window_streak(sb, 1, 5, 4) == 0


def test_static_timing_action_cards_uses_top_window_labels() -> None:
    cards = static_timing_action_cards({"day": "Thứ 7", "hours": "18–20", "lift_multiplier": 2.8})
    assert len(cards) == 2
    assert "Thứ 7" in cards[0].title
    assert "18–20" in cards[0].title
    assert cards[0].forecast["expected_range"].endswith("× median")
