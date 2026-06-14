"""Structure-driven retention curve (v1) — deterministic unit tests."""

from __future__ import annotations

from getviews_pipeline.services.extraction import _summarise_retention_curve
from getviews_pipeline.video_structural import (
    model_retention_curve,
    model_retention_curve_from_structure,
)


def _curve_end(curve: list[dict]) -> float:
    return float(curve[-1]["pct"])


def test_dead_air_asr_localizes_risk_event() -> None:
    scenes = [
        {"type": "face_to_camera", "start": 0.0, "end": 2.0, "pace": "medium", "motion": "handheld"},
        {"type": "demo", "start": 4.5, "end": 10.0, "pace": "fast", "motion": "handheld"},
    ]
    asr = [
        {"start_sec": 0.0, "end_sec": 1.8, "text": "xin chào"},
        {"start_sec": 4.5, "end_sec": 6.0, "text": "bắt đầu demo"},
    ]
    curve, events = model_retention_curve_from_structure(
        12.0,
        scenes,
        niche_median_retention=0.45,
        breakout_multiplier=1.0,
        asr_segments=asr,
        audio_track_role="spoken_overlay",
    )
    assert len(curve) == 20
    assert events
    assert any(e.get("source") == "asr" for e in events)
    assert any("lặng" in str(e.get("reason_vi") or "") for e in events)


def test_over_long_static_scene_risk() -> None:
    scenes = [
        {
            "type": "product_shot",
            "start": 0.0,
            "end": 8.0,
            "pace": "static",
            "motion": "static",
            "subject": "product",
        },
        {"type": "face_to_camera", "start": 8.0, "end": 12.0, "pace": "fast", "motion": "handheld"},
    ]
    curve, events = model_retention_curve_from_structure(
        12.0,
        scenes,
        niche_median_retention=0.5,
        breakout_multiplier=1.0,
    )
    assert any("tĩnh" in str(e.get("reason_vi") or "") for e in events)
    mid = [p for p in curve if 2.0 <= p["t"] <= 9.0]
    assert mid
    assert mid[0]["pct"] <= 100.0


def test_end_retention_anchored_to_niche_median() -> None:
    niche_ret = 0.42
    expected_end = 42.0
    scenes = [
        {"type": "face_to_camera", "start": 0.0, "end": 3.0, "pace": "fast"},
        {"type": "demo", "start": 3.0, "end": 20.0, "pace": "fast"},
    ]
    curve, _ = model_retention_curve_from_structure(
        20.0,
        scenes,
        niche_median_retention=niche_ret,
        breakout_multiplier=1.2,
    )
    assert abs(_curve_end(curve) - expected_end) < 1.5


def test_no_scenes_matches_synthetic_fallback() -> None:
    syn = model_retention_curve(15.0, niche_median_retention=0.45, breakout_multiplier=1.0)
    struct, events = model_retention_curve_from_structure(
        15.0,
        [],
        niche_median_retention=0.45,
        breakout_multiplier=1.0,
    )
    # Empty scenes still produce a curve via default opening risk — caller gates fallback.
    assert not events or struct
    assert abs(_curve_end(syn) - _curve_end(struct)) < 15.0


def test_monotonic_ish_no_large_rebounds() -> None:
    scenes = [
        {"type": "face_to_camera", "start": 0.0, "end": 2.0, "pace": "medium"},
        {"type": "demo", "start": 2.0, "end": 5.0, "pace": "fast"},
        {"type": "cta", "start": 5.0, "end": 10.0, "pace": "medium"},
    ]
    curve, _ = model_retention_curve_from_structure(
        10.0,
        scenes,
        niche_median_retention=0.4,
    )
    for i in range(1, len(curve)):
        assert curve[i]["pct"] <= curve[i - 1]["pct"] + 1.5


def test_approx_dead_air_without_asr_uses_window_phrasing() -> None:
    scenes = [
        {"type": "face_to_camera", "start": 0.0, "end": 2.0, "pace": "medium"},
        {"type": "demo", "start": 4.0, "end": 8.0, "pace": "fast"},
    ]
    _, events = model_retention_curve_from_structure(
        10.0,
        scenes,
        niche_median_retention=0.45,
        asr_segments=None,
        audio_track_role="spoken_overlay",
    )
    approx = [e for e in events if e.get("source") == "approx"]
    assert approx
    reason = str(approx[0].get("reason_vi") or "")
    assert "–" in reason or "ước tính" in reason


def test_correlate_structural_drop_vs_breakout_synthetic() -> None:
    from getviews_pipeline.viral_alignment_backtest import correlate_structural_drop_vs_breakout

    rows = []
    for i, bm in enumerate([0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]):
        rows.append(
            {
                "breakout_multiplier": bm,
                "duration_sec": 20.0,
                "avg_retention": 0.45,
                "analysis_json": {
                    "scenes": [
                        {
                            "type": "face_to_camera",
                            "start": 0.0,
                            "end": 3.0 + i * 0.5,
                            "pace": "static" if i > 4 else "fast",
                            "motion": "static" if i > 4 else "handheld",
                        },
                        {"type": "demo", "start": 8.0, "end": 20.0, "pace": "fast"},
                    ],
                    "hook_analysis": {
                        "hook_body_contract": i < 4,
                        "first_frame_type": "face",
                    },
                },
            }
        )
    out = correlate_structural_drop_vs_breakout(rows)
    assert out["n"] >= 5
    assert out["spearman_rho_early_drop_vs_breakout"] is not None


def test_summarise_retention_curve_named_drop_with_risk_events() -> None:
    curve = [
        {"t": 0.0, "pct": 100.0},
        {"t": 3.0, "pct": 85.0},
        {"t": 6.0, "pct": 60.0},
        {"t": 10.0, "pct": 45.0},
    ]
    events = [{"t": 6.0, "severity": 0.8, "reason_vi": "khoảng lặng ~0:06", "source": "asr"}]
    summary = _summarise_retention_curve(curve, events)
    assert "Drop lớn nhất ~0:06" in summary
    assert "khoảng lặng" in summary


def test_summarise_retention_curve_scene_source_omits_precise_second() -> None:
    curve = [
        {"t": 0.0, "pct": 100.0},
        {"t": 3.0, "pct": 85.0},
        {"t": 6.0, "pct": 60.0},
        {"t": 10.0, "pct": 45.0},
    ]
    events = [
        {"t": 6.0, "severity": 0.8, "reason_vi": "cảnh tĩnh dài 0:03–0:09", "source": "scene"}
    ]
    summary = _summarise_retention_curve(curve, events)
    # Window phrasing preserved; no false-precise "~m:ss" prefix for non-ASR source.
    assert "Drop lớn nhất:" in summary
    assert "~0:06" not in summary
    assert "cảnh tĩnh dài 0:03–0:09" in summary
