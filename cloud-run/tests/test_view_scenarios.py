"""``compute_view_scenarios`` — baseline + conditional rows + full_rewrite tail."""

from __future__ import annotations

from getviews_pipeline.pipelines import compute_view_scenarios

MOCK_ERRORS_WITH_HOOK = [
    {
        "error_id": "hook_weak",
        "sev": "high",
        "title": "Hook",
        "detail": "",
        "fix": "",
        "t": 0.0,
        "end": 1.0,
    },
    {
        "error_id": "visual_clutter",
        "sev": "mid",
        "title": "Visual",
        "detail": "",
        "fix": "",
        "t": 0.0,
        "end": 1.0,
    },
]

MOCK_ERRORS_EMPTY: list[dict] = []


def test_view_scenarios_has_baseline_and_full_rewrite() -> None:
    scenarios = compute_view_scenarios(231, MOCK_ERRORS_WITH_HOOK, 2400, 50000)
    assert scenarios[0]["scenario_id"] == "baseline"
    assert scenarios[-1]["scenario_id"] == "full_rewrite"
    assert len(scenarios) >= 2


def test_view_scenarios_hook_only_when_high_sev() -> None:
    scenarios = compute_view_scenarios(231, MOCK_ERRORS_WITH_HOOK, 2400, 50000)
    ids = [s["scenario_id"] for s in scenarios]
    assert "hook_only" in ids


def test_view_scenarios_without_errors_still_full_rewrite() -> None:
    scenarios = compute_view_scenarios(231, MOCK_ERRORS_EMPTY, 2400, 50000)
    assert scenarios[0]["scenario_id"] == "baseline"
    assert scenarios[-1]["scenario_id"] == "full_rewrite"
    assert all(s["scenario_id"] != "hook_only" for s in scenarios)


def test_view_scenarios_missing_averages_null_projection() -> None:
    scenarios = compute_view_scenarios(231, MOCK_ERRORS_WITH_HOOK, None, None)
    full = next(s for s in scenarios if s["scenario_id"] == "full_rewrite")
    assert full.get("projected_views") is None


def test_view_scenarios_zero_views_baseline() -> None:
    scenarios = compute_view_scenarios(0, [], 0, None)
    assert scenarios[0]["projected_views"] == 0
