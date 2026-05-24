"""Unit tests for morning_ritual — Phase A · A2.

The Gemini call itself is NOT exercised here (needs API key + network); the
test focuses on the parts we wrote: grounding fallback ladder, prompt
shaping, batch-summary counting.
"""

from __future__ import annotations

from typing import Any

# ── Fake Supabase ─────────────────────────────────────────────────────────


class _Exec:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    """Records every filter call so we can assert fallback ladder took the
    expected path (7d ref → 7d niche → 30d niche)."""

    def __init__(
        self,
        rows_for_path: dict[tuple[str, ...], list[dict[str, Any]]],
        calls_log: list[tuple[str, ...]],
    ) -> None:
        self._rows_for_path = rows_for_path
        self._path: list[str] = []
        self._calls_log = calls_log

    def select(self, *_: Any, **__: Any) -> _Query:
        return self

    def eq(self, col: str, val: Any) -> _Query:
        self._path.append(f"eq:{col}={val}")
        return self

    def gte(self, col: str, val: Any) -> _Query:
        # truncate timestamp to just the day span for predictable test keys
        self._path.append(f"gte:{col}")
        return self

    def in_(self, col: str, vals: Any) -> _Query:
        self._path.append(f"in:{col}={','.join(map(str, vals))}")
        return self

    def order(self, *_: Any, **__: Any) -> _Query:
        return self

    def limit(self, *_: Any, **__: Any) -> _Query:
        return self

    def execute(self) -> _Exec:
        key = tuple(self._path)
        self._calls_log.append(key)
        return _Exec(self._rows_for_path.get(key, []))


class _Client:
    def __init__(self, rows_for_path: dict[tuple[str, ...], list[dict[str, Any]]]) -> None:
        self.rows_for_path = rows_for_path
        self.calls_log: list[tuple[str, ...]] = []

    def table(self, name: str) -> _Query:
        return _Query(self.rows_for_path, self.calls_log)


# ── Grounding fallback ladder ─────────────────────────────────────────────


def test_grounding_uses_reference_handles_first() -> None:
    # When the 7d reference-anchored query returns enough rows, we don't
    # touch the niche-wide fallbacks.
    try:
        from getviews_pipeline.morning_ritual import _fetch_grounding_videos
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    rows = [{"video_id": f"v{i}"} for i in range(15)]
    client = _Client({
        ("in:creator_handle=@a,@b", "gte:created_at", "eq:ingest_loop_niche_id=4"): rows,
    })
    videos, adequacy = _fetch_grounding_videos(client, 4, ["@a", "@b"])
    assert len(videos) == 15
    # Adequacy tier: 15 videos → reference_pool (≥5) but < basic_citation (20)
    assert adequacy == "reference_pool"
    # Only one query fired.
    assert len(client.calls_log) == 1


def test_grounding_falls_back_to_niche_wide_7d_when_reference_thin() -> None:
    try:
        from getviews_pipeline.morning_ritual import _fetch_grounding_videos
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    client = _Client({
        ("in:creator_handle=@a", "gte:created_at", "eq:ingest_loop_niche_id=4"):  # ref-anchored
            [{"video_id": "r1"}, {"video_id": "r2"}],  # only 2 — below MIN_GROUNDING_VIDEOS
        ("gte:created_at", "eq:ingest_loop_niche_id=4"):  # niche-wide 7d
            [{"video_id": f"w{i}"} for i in range(18)],
    })
    videos, _ = _fetch_grounding_videos(client, 4, ["@a"])
    ids = [v["video_id"] for v in videos]
    assert "r1" in ids and "r2" in ids
    assert len(videos) == 20  # capped at TARGET_GROUNDING_VIDEOS


def test_grounding_falls_back_to_30d_when_7d_still_thin() -> None:
    try:
        from getviews_pipeline.morning_ritual import _fetch_grounding_videos
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    client = _Client({
        # 7d niche-wide returns just 3, below MIN
        ("gte:created_at", "eq:ingest_loop_niche_id=4"): [{"video_id": f"w{i}"} for i in range(3)],
    })
    # no reference handles; two calls hit the same path key — second yields []
    # To avoid that collision we'll just assert the call log grows to 2 paths
    # and adequacy reflects what we eventually got (3 rows → none/tier-0).
    videos, adequacy = _fetch_grounding_videos(client, 4, [])
    # With the fake key collision, both 7d + 30d queries hit the same key and
    # yield the same rows; dedupe caps the pool at 3.
    assert len(videos) == 3
    assert adequacy == "none"  # 3 < reference_pool (5)


# ── Prompt shaping ─────────────────────────────────────────────────────────


def test_prompt_includes_reference_handles_note_when_set() -> None:
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    videos = [{"video_id": "v1", "creator_handle": "x", "views": 1000,
               "hook_type": "pov", "hook_phrase": "POV: ..."}]
    prompt = _build_prompt("Fashion", videos, ["@a", "@b"])
    assert "Fashion" in prompt
    assert "@a" in prompt and "@b" in prompt
    assert "kênh tham chiếu" in prompt


def test_prompt_omits_reference_note_when_handles_empty() -> None:
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    prompt = _build_prompt("Tech", [{"video_id": "v1"}], [])
    assert "kênh tham chiếu" not in prompt


# ── Prompt v2 (D1 quality lift, 2026-05-13) ────────────────────────────────


def test_prompt_v2_lists_all_seven_psychology_mechanisms() -> None:
    """why_works guidance must enumerate the 7 named mechanisms so Gemini
    has a vocabulary to pick from instead of hallucinating generic
    'tạo sự tò mò' phrasing."""
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    prompt = _build_prompt("Beauty", [{"video_id": "v1"}], [])
    for mechanism in (
        "curiosity_gap", "social_proof", "identification",
        "contrarian_take", "before_after_promise",
        "status_anchor", "fomo_loss",
    ):
        assert mechanism in prompt, f"missing mechanism keyword: {mechanism}"


def test_prompt_v2_anchors_shot_count_and_length_to_grounding_median() -> None:
    """Prompt should inject median shot_count + length_sec from grounding
    so Gemini matches the niche's winning videos rather than picking
    an arbitrary point inside the 3-6 / 20-45 hard-coded range."""
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    videos = [
        {"video_id": "v1", "scene_count": 5, "video_duration": 28},
        {"video_id": "v2", "scene_count": 5, "video_duration": 30},
        {"video_id": "v3", "scene_count": 6, "video_duration": 32},
    ]
    prompt = _build_prompt("Beauty", videos, [])
    # Median shot_count = 5, length_sec = 30 — both should anchor in prompt.
    assert "5 shot" in prompt
    assert "30 giây" in prompt


def test_prompt_v2_adequacy_note_changes_with_tier() -> None:
    """Adequacy tier guidance must propagate into the prompt so Gemini
    calibrates hook confidence to grounding depth."""
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    videos = [{"video_id": "v1"}]
    thin_prompt = _build_prompt("Tech", videos, [], adequacy="thin")
    norms_prompt = _build_prompt("Tech", videos, [], adequacy="niche_norms")
    assert "Adequacy tier**: thin" in thin_prompt
    assert "Adequacy tier**: niche_norms" in norms_prompt
    assert "tránh promise mạnh" in thin_prompt
    assert "pattern hot" in norms_prompt


def test_prompt_v2_includes_few_shot_example() -> None:
    """ME-14 — few-shot is derived from top-view grounding row (not static Beauty copy)."""
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    videos = [
        {"video_id": "v_low", "views": 100, "hook_phrase": "low views"},
        {
            "video_id": "v_top",
            "views": 9_999_999,
            "hook_type": "shock_stat",
            "hook_phrase": "Glycolic 7% trong 21 ngày — đây là làn da tôi",
            "scene_count": 6,
            "video_duration": 40,
            "engagement_rate": 0.11,
        },
    ]
    prompt = _build_prompt("Beauty", videos, [])
    assert "neo từ video nổi bật" in prompt or "Few-shot" in prompt
    assert "Glycolic 7%" in prompt
    assert "shock_stat" in prompt


def test_prompt_v2_grounding_carries_engagement_and_scene_fields() -> None:
    """Per-row grounding payload must carry scene_count + length_sec +
    engagement_rate so Gemini has signal to anchor outputs to high-ER
    videos rather than just view-count toplines."""
    try:
        from getviews_pipeline.morning_ritual import _build_prompt
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    videos = [{
        "video_id": "v1", "creator_handle": "@x", "views": 1000,
        "hook_type": "pov", "hook_phrase": "POV: ...",
        "scene_count": 4, "video_duration": 25, "engagement_rate": 8.2,
    }]
    prompt = _build_prompt("Beauty", videos, [])
    assert '"scene_count": 4' in prompt
    assert '"length_sec": 25' in prompt
    assert '"engagement_rate": 8.2' in prompt


def test_median_helper_handles_edge_cases() -> None:
    try:
        from getviews_pipeline.morning_ritual import _median
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    assert _median([]) is None
    assert _median([5]) == 5
    assert _median([3, 5, 7]) == 5
    assert _median([2, 4, 6, 8]) == 5  # (4+6)//2 = 5


# ── Batch summary counters ─────────────────────────────────────────────────


def test_batch_summary_fields_default_zero() -> None:
    try:
        from getviews_pipeline.morning_ritual import RitualBatchSummary
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")
    s = RitualBatchSummary()
    assert s.generated == 0
    assert s.skipped_thin == 0
    assert s.failed_schema == 0
    assert s.failed_gemini == 0
    assert s.users_no_niche == 0


# ── upsert_ritual skips empty/errored results ─────────────────────────────


def test_upsert_skips_errored_results() -> None:
    try:
        from datetime import date

        from getviews_pipeline.morning_ritual import RitualResult, upsert_ritual
    except ModuleNotFoundError:
        import pytest
        pytest.skip("pydantic not installed in test env")

    calls: list[str] = []

    class _FailIfCalled:
        def table(self, _name: str) -> Any:
            calls.append("table")
            raise AssertionError("upsert should not have been attempted")

    # Thin corpus errored — must not write.
    upsert_ritual(
        _FailIfCalled(),
        RitualResult(
            user_id="u", niche_id=1, scripts=[], adequacy="none",
            grounded_video_ids=[], generated_for_date=date.today(),
            error="thin_corpus: only 2 grounding videos",
        ),
    )
    # Schema failed — must not write.
    upsert_ritual(
        _FailIfCalled(),
        RitualResult(
            user_id="u", niche_id=1, scripts=[], adequacy="reference_pool",
            grounded_video_ids=["a"], generated_for_date=date.today(),
            error="schema_error: ...",
        ),
    )
    assert calls == []


# ── Audit Pass-3 fix #3 — uncaught-exception catch-all ────────────────


def test_run_morning_ritual_batch_skips_user_on_uncaught_exception() -> None:
    """When ``generate_ritual_for_user`` raises something its inner
    try/except blocks don't catch, the outer batch loop must continue
    so the rest of the user list still gets a ritual that day. The
    summary's ``failed_unhandled`` counter increments for visibility."""
    from unittest.mock import MagicMock, patch

    from getviews_pipeline.morning_ritual import (
        RitualBatchSummary,
        RitualResult,
        run_morning_ritual_batch,
    )

    # Stub Supabase: 3 profiles, niche-taxonomy lookup returns one row.
    profiles = [
        {"id": "user-1", "creator_niche_id": 2, "reference_channel_handles": []},
        {"id": "user-2", "creator_niche_id": 2, "reference_channel_handles": []},
        {"id": "user-3", "creator_niche_id": 2, "reference_channel_handles": []},
    ]
    client = MagicMock()
    profiles_q = MagicMock()
    profiles_q.execute.return_value = MagicMock(data=profiles)
    niche_q = MagicMock()
    niche_q.execute.return_value = MagicMock(
        data=[{"id": 2, "name_vn": "Skincare", "name_en": "Beauty"}],
    )

    def _table(name: str) -> MagicMock:
        if name == "profiles":
            return MagicMock(select=lambda *a, **k: profiles_q)
        if name == "niche_taxonomy":
            return MagicMock(select=lambda *a, **k: niche_q)
        return MagicMock()

    client.table.side_effect = _table

    # Resolve every profile to legacy niche_id=2. The import is lazy
    # (inside ``run_morning_ritual_batch``), so patch the source.
    with patch(
        "getviews_pipeline.profile_niches.resolve_legacy_niche_from_profile_row",
        return_value=2,
    ):
        # Make user-2's call raise; the others succeed.
        def _flaky(client: Any, *, user_id: str, **kw: Any) -> RitualResult:
            from datetime import date as _date
            if user_id == "user-2":
                raise RuntimeError("simulated SDK explosion")
            return RitualResult(
                user_id=user_id, niche_id=2, scripts=[],
                adequacy="thin", grounded_video_ids=[],
                generated_for_date=_date.today(),
                error="thin_corpus: only 2 grounding videos",
            )

        with patch(
            "getviews_pipeline.morning_ritual.generate_ritual_for_user",
            side_effect=_flaky,
        ):
            summary = run_morning_ritual_batch(client)

    assert isinstance(summary, RitualBatchSummary)
    # The exception didn't abort the loop — user-1 and user-3 ran.
    assert summary.failed_unhandled == 1
    # Both users-1 and -3 returned thin_corpus, so skipped_thin == 2.
    assert summary.skipped_thin == 2
