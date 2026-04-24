"""Wave 4 PR #2 — compare orchestration tests.

Pins:

* ``_stats`` extracts metrics from the run_video_diagnosis output
  shape; tolerates missing fields.
* Numeric delta helpers (signed_diff, hook_alignment, higher_breakout)
  return well-formed ``None`` / ``"unknown"`` on missing data.
* ``_templated_verdict`` covers the three higher-side cases + the
  three hook-alignment cases; output is always ≤ 240 chars.
* ``build_delta`` falls back to the templated verdict when Gemini
  fails OR when Gemini's output trips ``voice_lint``; the
  ``verdict_fallback`` flag flips True so observability sees it.
* ``run_compare_pipeline`` parallelizes two diagnoses, builds a
  ``ComparePayload``, and gracefully surfaces partial-failure
  (one side raises) without aborting the whole turn.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from getviews_pipeline.report_compare import (
    CompareDelta,
    ComparePayload,
    _higher_breakout,
    _hook_alignment,
    _signed_diff,
    _stats,
    _templated_verdict,
    build_delta,
    run_compare_pipeline,
)

# ── Sample inputs ────────────────────────────────────────────────────


def _diagnosis(
    *,
    handle: str = "creator_x",
    views: int | None = 100_000,
    breakout: float | None = 1.5,
    hook_type: str | None = "question",
    scene_count: int = 5,
    tps: float | None = 0.4,
    niche: str = "skincare",
) -> dict[str, Any]:
    """Mimic the run_video_diagnosis output dict — only the keys
    build_delta + run_compare_pipeline read."""
    return {
        "intent": "video_diagnosis",
        "niche": niche,
        "metadata": {
            "metrics": {"views": views},
            "breakout": breakout,
            "engagement_rate": 4.5,
            "author": {"username": handle},
        },
        "analysis": {
            "scenes": [{"i": i} for i in range(scene_count)],
            "transitions_per_second": tps,
            "hook_analysis": {"hook_type": hook_type},
        },
    }


# ── _stats normalisation ────────────────────────────────────────────


def test_stats_extracts_all_known_fields() -> None:
    s = _stats(_diagnosis(handle="left", views=50_000, breakout=2.1, hook_type="bold_claim"))
    assert s["views"] == 50_000
    assert s["breakout"] == 2.1
    assert s["hook_type"] == "bold_claim"
    assert s["scene_count"] == 5
    assert s["transitions_per_second"] == 0.4
    assert s["handle"] == "left"


def test_stats_tolerates_missing_metadata() -> None:
    s = _stats({})
    # Every key present, all None — the FE never sees an undefined-
    # key surprise.
    for k in ("views", "breakout", "engagement_rate", "scene_count",
              "transitions_per_second", "hook_type", "handle"):
        assert k in s


def test_stats_returns_none_scene_count_when_scenes_missing() -> None:
    """Empty scenes list → None (not 0). Lets the FE render '—'
    instead of a misleading zero."""
    s = _stats({"analysis": {"scenes": []}})
    assert s["scene_count"] is None


# ── Numeric helpers ─────────────────────────────────────────────────


def test_signed_diff_basic() -> None:
    assert _signed_diff(2.0, 1.0) == pytest.approx(1.0)
    assert _signed_diff(1.0, 2.0) == pytest.approx(-1.0)
    assert _signed_diff(None, 1.0) is None
    assert _signed_diff(1.0, None) is None


def test_hook_alignment_match_conflict_unknown() -> None:
    assert _hook_alignment("question", "question") == "match"
    assert _hook_alignment("question", "bold_claim") == "conflict"
    assert _hook_alignment(None, "question") == "unknown"
    assert _hook_alignment("question", None) == "unknown"
    assert _hook_alignment("", "question") == "unknown"  # empty ≈ missing


def test_higher_breakout_includes_tie_threshold() -> None:
    assert _higher_breakout(2.0, 1.5) == "left"
    assert _higher_breakout(1.5, 2.0) == "right"
    # Strict ``< 0.05`` → very-close pairs round to "tie" so trivial
    # noise doesn't pretend to pick a winner.
    assert _higher_breakout(1.5, 1.51) == "tie"
    assert _higher_breakout(1.5, 1.549) == "tie"  # just inside the band
    # At-or-above the threshold breaks the tie.
    assert _higher_breakout(1.5, 1.55) == "right"
    assert _higher_breakout(None, 1.5) == "unknown"


# ── Templated verdict ───────────────────────────────────────────────


def test_templated_verdict_left_higher_with_matching_hook() -> None:
    left = _stats(_diagnosis(hook_type="question"))
    right = _stats(_diagnosis(hook_type="question", breakout=1.0))
    v = _templated_verdict(left, right, "left", "match")
    assert "trái" in v
    assert "cùng kiểu hook" in v
    assert len(v) <= 240


def test_templated_verdict_conflict_lists_both_hooks() -> None:
    left = _stats(_diagnosis(hook_type="question"))
    right = _stats(_diagnosis(hook_type="bold_claim", breakout=1.0))
    v = _templated_verdict(left, right, "left", "conflict")
    assert "question" in v and "bold_claim" in v


def test_templated_verdict_tie_does_not_pick_a_side() -> None:
    left = _stats(_diagnosis())
    right = _stats(_diagnosis())
    v = _templated_verdict(left, right, "tie", "match")
    assert "tương đương" in v
    # Don't claim a winner.
    assert "trái" not in v
    assert "phải" not in v


def test_templated_verdict_unknown_higher_states_data_gap() -> None:
    left = _stats({})
    right = _stats({})
    v = _templated_verdict(left, right, "unknown", "unknown")
    assert "Chưa đủ" in v


# ── build_delta + Gemini fallback ───────────────────────────────────


def test_build_delta_uses_gemini_verdict_when_clean() -> None:
    left = _diagnosis(handle="a", breakout=2.0, hook_type="question")
    right = _diagnosis(handle="b", breakout=1.0, hook_type="question")
    with patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="Video trái chạy 2x so với phải - cùng hook nhưng pacing khác.",
    ):
        delta = build_delta(left, right, niche="skincare")
    assert delta.verdict_fallback is False
    assert "trái" in delta.verdict.lower()
    assert delta.higher_breakout_side == "left"
    assert delta.hook_alignment == "match"


def test_build_delta_falls_back_when_gemini_returns_none() -> None:
    left = _diagnosis(breakout=2.0)
    right = _diagnosis(breakout=1.0)
    with patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value=None,
    ):
        delta = build_delta(left, right, niche="skincare")
    assert delta.verdict_fallback is True
    # Templated verdict for left-higher.
    assert "trái" in delta.verdict


def test_build_delta_falls_back_when_gemini_trips_voice_lint() -> None:
    """Voice-lint enforcement: if Gemini emits a forbidden word, we
    drop the response and use the templated verdict instead. Never
    surface forbidden copy to creators."""
    left = _diagnosis(breakout=2.0)
    right = _diagnosis(breakout=1.0)
    forbidden = "Video trái bùng nổ hoàn toàn vượt phải - công thức vàng đây."
    with patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value=forbidden,
    ):
        delta = build_delta(left, right, niche="skincare")
    assert delta.verdict_fallback is True
    assert "bùng nổ" not in delta.verdict
    assert "công thức vàng" not in delta.verdict


def test_build_delta_skips_gemini_when_disabled() -> None:
    left = _diagnosis(breakout=2.0)
    right = _diagnosis(breakout=1.0)
    delta = build_delta(left, right, niche="skincare", gemini_enabled=False)
    assert delta.verdict_fallback is True
    assert delta.verdict  # always emits something


def test_build_delta_pins_numeric_outputs() -> None:
    left = _diagnosis(breakout=2.0, scene_count=8, tps=0.6)
    right = _diagnosis(breakout=1.5, scene_count=5, tps=0.4)
    with patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="Video trái mạnh hơn về mọi mặt.",
    ):
        delta = build_delta(left, right, niche="skincare")
    assert delta.breakout_gap == pytest.approx(0.5)
    assert delta.scene_count_diff == 3
    assert delta.transitions_per_second_diff == pytest.approx(0.2)


def test_build_delta_handles_missing_breakout() -> None:
    left = _diagnosis(breakout=None)
    right = _diagnosis(breakout=1.0)
    with patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value=None,
    ):
        delta = build_delta(left, right, niche="skincare")
    assert delta.breakout_gap is None
    assert delta.higher_breakout_side == "unknown"


# ── ComparePayload validation ───────────────────────────────────────


def test_compare_payload_pins_intent_literal() -> None:
    """The ``intent`` field is a Literal — Pydantic refuses anything
    else, so the FE discriminator can't drift."""
    delta = CompareDelta(
        verdict="OK", hook_alignment="match", higher_breakout_side="tie",
    )
    p = ComparePayload(left={"x": 1}, right={"y": 2}, delta=delta)
    assert p.intent == "compare_videos"
    assert p.model_dump()["intent"] == "compare_videos"


# ── run_compare_pipeline orchestration ──────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_parallelizes_and_assembles_payload() -> None:
    """Both diagnoses run; payload includes both + a delta."""
    left = _diagnosis(handle="a", breakout=2.0, hook_type="question")
    right = _diagnosis(handle="b", breakout=1.0, hook_type="bold_claim")

    async def _fake_diag(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return left if url.endswith("/1") else right

    with patch(
        "getviews_pipeline.pipelines.run_video_diagnosis",
        side_effect=_fake_diag,
    ), patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="Video trái mạnh hơn 2x — hook khác kiểu.",
    ):
        out = await run_compare_pipeline(
            "https://www.tiktok.com/@a/video/1",
            "https://www.tiktok.com/@b/video/2",
            session={"niche": "skincare"},
        )

    assert out["intent"] == "compare_videos"
    assert out["niche"] == "skincare"
    assert out["left"]["metadata"]["author"]["username"] == "a"
    assert out["right"]["metadata"]["author"]["username"] == "b"
    assert out["delta"]["higher_breakout_side"] == "left"
    assert out["delta"]["hook_alignment"] == "conflict"


@pytest.mark.asyncio
async def test_orchestrator_runs_both_in_parallel() -> None:
    """Total wall time should be ~max(left, right), not left + right."""
    started: list[float] = []

    async def _slow_diag(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        started.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.05)
        return _diagnosis()

    t0 = asyncio.get_event_loop().time()
    with patch(
        "getviews_pipeline.pipelines.run_video_diagnosis",
        side_effect=_slow_diag,
    ), patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="OK.",
    ):
        await run_compare_pipeline("u1", "u2", session={})
    elapsed = asyncio.get_event_loop().time() - t0
    # Two 50ms diagnoses in parallel should take ~50ms; sequential
    # would be ~100ms+. Loose threshold to avoid CI flakes.
    assert elapsed < 0.085, f"compare ran sequentially, elapsed={elapsed:.3f}s"
    # Both started within 10ms of each other — true parallelism.
    assert len(started) == 2
    assert abs(started[1] - started[0]) < 0.010


@pytest.mark.asyncio
async def test_orchestrator_passes_independent_session_copies() -> None:
    """Mutations inside one run_video_diagnosis must not race the other."""
    seen_sessions: list[int] = []

    async def _fake_diag(
        url: str,
        session: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Each side gets a distinct dict object — id() differs.
        seen_sessions.append(id(session))
        # Mutate ours; the other side's dict must not see this.
        session["mutated_by"] = url
        return _diagnosis()

    base_session: dict[str, Any] = {"niche": "skincare"}
    with patch(
        "getviews_pipeline.pipelines.run_video_diagnosis",
        side_effect=_fake_diag,
    ), patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="OK.",
    ):
        await run_compare_pipeline("u1", "u2", session=base_session)

    assert len(seen_sessions) == 2
    assert seen_sessions[0] != seen_sessions[1]
    # Outer session also untouched — copy isolation works both ways.
    assert "mutated_by" not in base_session


@pytest.mark.asyncio
async def test_orchestrator_left_failure_returns_right_only() -> None:
    """Partial failure: one side raises → return the other side's
    diagnosis as a single-video fallback. Better than an SSE error
    when the user can still get half of what they paid for."""
    right = _diagnosis(handle="b")

    async def _fake_diag(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/1"):
            raise RuntimeError("boom on left")
        return right

    with patch(
        "getviews_pipeline.pipelines.run_video_diagnosis",
        side_effect=_fake_diag,
    ), patch(
        "getviews_pipeline.report_compare._call_delta_gemini",
        return_value="N/A.",
    ):
        out = await run_compare_pipeline(
            "https://www.tiktok.com/@a/video/1",
            "https://www.tiktok.com/@b/video/2",
            session={},
        )
    # Single-video fallback shape, not the compare shape.
    assert out["intent"] == "video_diagnosis"
    assert out["metadata"]["author"]["username"] == "b"


@pytest.mark.asyncio
async def test_orchestrator_both_failures_propagate() -> None:
    """If both sides raise, surface the failure so /stream emits its
    standard error envelope rather than silently dropping the request."""
    async def _fake_diag(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("both sides down")

    with patch(
        "getviews_pipeline.pipelines.run_video_diagnosis",
        side_effect=_fake_diag,
    ):
        with pytest.raises(RuntimeError, match="both sides down"):
            await run_compare_pipeline("u1", "u2", session={})
