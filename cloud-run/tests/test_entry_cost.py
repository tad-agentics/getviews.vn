"""Unit tests for score_entry_cost."""

from __future__ import annotations

from getviews_pipeline.entry_cost import score_entry_cost


def _mk(
    *,
    tps: float = 0.5,
    scenes: list[dict] | None = None,
    energy: str = "medium",
    overlays: int = 0,
) -> dict:
    return {
        "transitions_per_second": tps,
        "scenes": scenes or [],
        "energy_level": energy,
        "text_overlays": [{"text": f"t{i}", "appears_at": float(i)} for i in range(overlays)],
    }


def test_phone_and_one_take_is_easy() -> None:
    # Talking-head GRWM: 2 scenes, low energy, no overlays.
    tier, _ = score_entry_cost(_mk(
        tps=0.3,
        scenes=[{"type": "face"}, {"type": "face"}],
        energy="low",
        overlays=0,
    ))
    assert tier == "easy"


def test_moderate_editing_is_medium() -> None:
    # 4 scenes, mix of face + product + screen, one overlay.
    tier, _ = score_entry_cost(_mk(
        tps=1.2,
        scenes=[
            {"type": "face"},
            {"type": "product"},
            {"type": "screen"},
            {"type": "face"},
        ],
        energy="medium",
        overlays=2,
    ))
    assert tier == "medium"


def test_production_grade_is_hard() -> None:
    # 10 scenes, 4 scene types, high energy, many overlays, fast cuts.
    tier, reasons = score_entry_cost(_mk(
        tps=2.1,
        scenes=[{"type": t} for t in ["face", "face", "face", "product", "product", "screen", "broll", "broll", "face", "product"]],
        energy="high",
        overlays=8,
    ))
    assert tier == "hard"
    assert len(reasons) >= 4


def test_reasons_are_vietnamese() -> None:
    _, reasons = score_entry_cost(_mk(
        tps=2.0,
        scenes=[{"type": "face"} for _ in range(8)],
        energy="high",
        overlays=6,
    ))
    # At least one Vietnamese-flavored reason must be present — each reason
    # may not always carry a diacritic (numbers + filler), but the set should.
    joined = " ".join(reasons)
    # Any char outside basic ASCII letters is evidence of Vietnamese text.
    assert any(ord(c) > 127 for c in joined)


def test_empty_analysis_defaults_to_easy() -> None:
    tier, reasons = score_entry_cost({})
    assert tier == "easy"
    assert reasons == []


def test_boundary_tps_exactly_1_5_stays_easy_without_other_signals() -> None:
    # rule is > 1.5, not >=
    tier, _ = score_entry_cost(_mk(tps=1.5))
    assert tier == "easy"


def test_single_strong_signal_stays_easy() -> None:
    # Just high energy alone — still feasible with phone + quick edit.
    tier, _ = score_entry_cost(_mk(energy="high"))
    assert tier == "easy"
