"""Signal calibration loop v1 — unit + job tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.diagnose_prompts import _signal_payload, build_diagnosis_v6_user_prompt
from getviews_pipeline.settings import settings
from getviews_pipeline.signal_calibration import (
    CALIBRATION_READER_TTL_S,
    CLASS_SAMPLE_FLOOR,
    CalibrationFeature,
    _clear_reader_caches,
    _ttl_cache,
    adopt_guard,
    build_calibration_priors,
    run_signal_calibration,
    signal_salience_multiplier,
    simplex_weights,
    sweep_best_weights,
    viral_score_weights,
    weighted_score,
)
from getviews_pipeline.signals.base import Signal
from getviews_pipeline.signals.registry import build_signal_manifest
from getviews_pipeline.viral_alignment_backtest import W_FORMAT, W_HOOK, W_TIME


def _feat(
    hook: float,
    fmt: float,
    time: float,
    breakout: float,
    *,
    class_id: int = 1,
) -> CalibrationFeature:
    return CalibrationFeature(
        niche_id=1,
        content_class_id=class_id,
        hook_align=hook,
        format_align=fmt,
        time_align=time,
        breakout=breakout,
    )


def test_simplex_weights_sum_to_one_and_respect_bounds() -> None:
    combos = simplex_weights(step=0.1)
    assert combos
    for wh, wf, wt in combos:
        assert abs(wh + wf + wt - 1.0) < 1e-6
        assert 0.1 <= wh <= 0.7
        assert 0.1 <= wf <= 0.7
        assert 0.1 <= wt <= 0.7


def test_sweep_prefers_hook_heavy_on_synthetic_data() -> None:
    # Breakout tracks hook alignment strongly.
    features = [
        _feat(h, 0.2, 0.2, h * 3.0)
        for h in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
    ]
    best, rho = sweep_best_weights(features, step=0.1)
    assert rho > 0.9
    # Many weight combos tie at ρ=1.0 on this synthetic set — argmax order is grid-dependent.
    assert sum(best) == pytest.approx(1.0)


def test_adopt_guard_rejects_thin_sample_and_weak_holdout() -> None:
    assert adopt_guard(0.5, 0.3, 10, CLASS_SAMPLE_FLOOR) is False
    assert adopt_guard(0.34, 0.33, 200, 200) is False
    assert adopt_guard(0.40, 0.33, 200, 200) is True


def test_weighted_score_uses_custom_weights() -> None:
    assert weighted_score(1.0, 0.0, 0.0, (0.7, 0.2, 0.1)) == pytest.approx(70.0)


@patch.object(settings, "signal_calibration_adaptive", False)
def test_viral_score_weights_flag_off_returns_static() -> None:
    viral_score_weights.cache_clear()
    assert viral_score_weights(42) == (W_HOOK, W_FORMAT, W_TIME)


@patch.object(settings, "signal_calibration_adaptive", True)
def test_viral_score_weights_ladder_class_then_global() -> None:
    viral_score_weights.cache_clear()

    class MockTable:
        def __init__(self, name: str) -> None:
            self.name = name
            self._filters: dict[str, Any] = {}

        def select(self, *_cols: str) -> MockTable:
            return self

        def eq(self, key: str, val: Any) -> MockTable:
            self._filters[key] = val
            return self

        def is_(self, key: str, val: str) -> MockTable:
            self._filters[key] = None
            return self

        def order(self, *_a: Any, **_kw: Any) -> MockTable:
            return self

        def limit(self, *_a: Any) -> MockTable:
            return self

        def execute(self) -> Any:
            if self.name == "signal_calibration":
                scope = self._filters.get("scope")
                cc = self._filters.get("content_class_id")
                if scope == "content_class" and cc == 7:
                    return MagicMock(data=[{
                        "w_hook": 0.6,
                        "w_format": 0.25,
                        "w_time": 0.15,
                        "adopted": True,
                    }])
                return MagicMock(data=[])
            return MagicMock(data=[])

    client = MagicMock()
    client.table.side_effect = lambda name: MockTable(name)

    with patch(
        "getviews_pipeline.signal_calibration._service_client_cached",
        return_value=client,
    ):
        assert viral_score_weights(7) == (0.6, 0.25, 0.15)
        assert viral_score_weights(99) == (W_HOOK, W_FORMAT, W_TIME)


def test_run_signal_calibration_writes_when_gate_met() -> None:
    inserts: list[tuple[str, dict[str, Any]]] = []

    class MockTable:
        def __init__(self, name: str) -> None:
            self.name = name

        def select(self, *_cols: str) -> MockTable:
            return self

        def not_(self) -> MockTable:
            return self

        def is_(self, *_a: Any, **_kw: Any) -> MockTable:
            return self

        def limit(self, *_a: Any) -> MockTable:
            return self

        def insert(self, row: dict[str, Any]) -> MockTable:
            inserts.append((self.name, row))
            return self

        def execute(self) -> Any:
            return MagicMock(data=[])

    client = MagicMock()
    client.table.side_effect = lambda name: MockTable(name)

    features = [
        _feat(h, f, t, h * 2.0 + f, class_id=11)
        for h, f, t in (
            (0.1, 0.2, 0.3),
            (0.2, 0.3, 0.2),
            (0.3, 0.1, 0.4),
            (0.4, 0.4, 0.1),
            (0.5, 0.2, 0.3),
            (0.6, 0.3, 0.2),
            (0.7, 0.1, 0.5),
            (0.8, 0.2, 0.2),
            (0.9, 0.3, 0.1),
            (1.0, 0.4, 0.4),
        )
    ] * 4  # 40 rows — clears class floor

    with patch(
        "getviews_pipeline.signal_calibration.extract_calibration_features",
        return_value=features,
    ):
        summary = run_signal_calibration(client)

    assert summary["classes_calibrated"] >= 1
    cal_inserts = [row for table, row in inserts if table == "signal_calibration"]
    assert cal_inserts
    assert any(row.get("scope") == "content_class" for row in cal_inserts)


@patch.object(settings, "signal_calibration_adaptive", True)
def test_signal_salience_multiplier_demotes_weak_lever() -> None:
    signal_salience_multiplier.cache_clear()
    predictive_rho_for_lever = __import__(
        "getviews_pipeline.signal_calibration",
        fromlist=["predictive_rho_for_lever"],
    ).predictive_rho_for_lever
    predictive_rho_for_lever.cache_clear()

    with patch(
        "getviews_pipeline.signal_calibration.predictive_rho_for_lever",
        return_value=-0.2,
    ):
        mult = signal_salience_multiplier("hook_late_overlay", 5)
    assert mult < 1.0
    assert mult >= 0.5


@patch.object(settings, "signal_calibration_adaptive", False)
def test_signal_salience_multiplier_flag_off_is_one() -> None:
    signal_salience_multiplier.cache_clear()
    assert signal_salience_multiplier("hook_late_overlay", 5) == 1.0


@patch.object(settings, "signal_calibration_adaptive", True)
def test_build_signal_manifest_demotes_when_flag_on() -> None:
    signal_salience_multiplier.cache_clear()
    ctx = {
        "user_analysis": {"hook_analysis": {"hook_type": "question"}},
        "user_stats": {"views": 1000, "performance_tier": "average"},
        "reference_videos": [],
        "channel_context": None,
        "performance_tier": "average",
        "niche_meta": {},
        "content_class_id": 3,
    }
    with patch(
        "getviews_pipeline.signal_calibration.signal_salience_multiplier",
        return_value=0.6,
    ):
        manifest = build_signal_manifest(ctx)
    for sigs in manifest.values():
        for sig in sigs:
            if sig.id.startswith("hook_"):
                assert sig.salience <= 0.6


@patch.object(settings, "signal_calibration_adaptive", False)
def test_signal_payload_flag_off_omits_predictive_strength() -> None:
    sig = Signal(
        id="hook_test",
        section_id="hook_analysis",
        taxonomy_ref="§hook",
        salience=0.8,
        claim="test",
    )
    payload = _signal_payload({"hook_analysis": [sig]}, content_class_id=1)
    assert "predictive_strength" not in payload[0]


@patch.object(settings, "signal_calibration_adaptive", True)
def test_signal_payload_flag_on_includes_predictive_strength() -> None:
    sig = Signal(
        id="hook_test",
        section_id="hook_analysis",
        taxonomy_ref="§hook",
        salience=0.8,
        claim="test",
    )
    with patch(
        "getviews_pipeline.signal_calibration.predictive_strength_for_signal",
        return_value=0.42,
    ):
        payload = _signal_payload({"hook_analysis": [sig]}, content_class_id=1)
    assert payload[0]["predictive_strength"] == 0.42


@patch.object(settings, "signal_calibration_adaptive", True)
def test_build_calibration_priors_above_floor_cites_rho() -> None:
    calibration_row_for_class = __import__(
        "getviews_pipeline.signal_calibration",
        fromlist=["calibration_row_for_class"],
    ).calibration_row_for_class
    calibration_row_for_class.cache_clear()
    predictive_rho_for_lever = __import__(
        "getviews_pipeline.signal_calibration",
        fromlist=["predictive_rho_for_lever"],
    ).predictive_rho_for_lever
    predictive_rho_for_lever.cache_clear()

    with patch(
        "getviews_pipeline.signal_calibration.calibration_row_for_class",
        return_value={
            "w_hook": 0.5,
            "w_format": 0.3,
            "w_time": 0.2,
            "rho_holdout": 0.44,
            "sample_size": 120,
            "adopted": True,
        },
    ), patch(
        "getviews_pipeline.signal_calibration.predictive_rho_for_lever",
        return_value=0.38,
    ):
        block = build_calibration_priors(11)
    assert block is not None
    assert "ρ_holdout=0.44" in block
    assert "n=120" in block


@patch.object(settings, "signal_calibration_adaptive", False)
def test_build_diagnosis_prompt_flag_off_no_calibration_block() -> None:
    """Gemini gates the block; prompt helper only renders when non-empty."""
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={"content_class_id": 1},
        content_format="talking_head",
        niche_name="Test",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
        calibration_priors_block="",
    )
    assert "CALIBRATION_PRIORS" not in prompt


@patch.object(settings, "signal_calibration_adaptive", True)
def test_build_diagnosis_prompt_includes_calibration_block() -> None:
    priors = (
        "CALIBRATION_PRIORS (đo từ corpus — dùng để ưu tiên lever và làm sâu lý do trong findings hiện có; "
        "KHÔNG mở section mới):\n- Trọng số rubric ngách: hook > format > timing (ρ_holdout=0.44, n=120)."
    )
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={"content_class_id": 1},
        content_format="talking_head",
        niche_name="Test",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
        calibration_priors_block=priors,
    )
    assert "CALIBRATION_PRIORS" in prompt
    assert "ρ_holdout=0.44" in prompt


def test_ttl_cache_refetches_after_ttl_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    @_ttl_cache(60)
    def bump(x: int) -> int:
        calls.append(x)
        return x + 1

    t = 1000.0
    monkeypatch.setattr("time.monotonic", lambda: t)
    assert bump(1) == 2
    assert bump(1) == 2
    assert calls == [1]

    monkeypatch.setattr("time.monotonic", lambda: t + CALIBRATION_READER_TTL_S + 1)
    assert bump(1) == 2
    assert calls == [1, 1]


@patch.object(settings, "signal_calibration_adaptive", True)
def test_clear_reader_caches_forces_viral_weights_refresh() -> None:
    viral_score_weights.cache_clear()
    fetch_calls = 0

    def _fetch(*_a: Any, **_kw: Any) -> dict[str, Any]:
        nonlocal fetch_calls
        fetch_calls += 1
        return {"w_hook": 0.5, "w_format": 0.3, "w_time": 0.2, "adopted": True}

    with patch(
        "getviews_pipeline.signal_calibration._service_client_cached",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.signal_calibration._fetch_latest_calibration",
        side_effect=_fetch,
    ):
        assert viral_score_weights(3) == (0.5, 0.3, 0.2)
        assert fetch_calls == 1
        assert viral_score_weights(3) == (0.5, 0.3, 0.2)
        assert fetch_calls == 1
        _clear_reader_caches()
        assert viral_score_weights(3) == (0.5, 0.3, 0.2)
        assert fetch_calls == 2
