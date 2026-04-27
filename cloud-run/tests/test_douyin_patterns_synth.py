"""D5b (2026-06-05) — Kho Douyin · weekly-patterns synth tests.

Mirrors the test taxonomy from ``test_douyin_synth.py``:
  • Pydantic validation (rank uniqueness, hook blank, sample-id uniq).
  • Public API contract (None on small pool / Gemini error / out-of-pool
    sample_video_ids).
  • lru_cache behaviour at the inner Gemini-call layer (patches
    ``_generate_content_models`` + ``_response_text`` so the cache is
    actually exercised, not bypassed).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from getviews_pipeline.douyin_patterns_synth import (
    MIN_INPUT_POOL,
    DouyinPatternEntry,
    DouyinPatternsSynth,
    DouyinPatternsSynthInputVideo,
    _reset_cache_for_tests,
    synth_douyin_patterns,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests() -> None:
    _reset_cache_for_tests()


# ── Helpers ────────────────────────────────────────────────────────


def _input_video(video_id: str = "v1", **overrides) -> DouyinPatternsSynthInputVideo:
    base = {
        "video_id": video_id,
        "title_zh": "睡前3件事",
        "title_vi": "3 việc trước khi ngủ",
        "hook_phrase": "睡前3件事",
        "hook_type": "curiosity_gap",
        "content_format": "voiceover_pov",
        "views": 500_000,
        "cn_rise_pct": 35.0,
    }
    base.update(overrides)
    return DouyinPatternsSynthInputVideo(**base)


def _input_pool(n: int = MIN_INPUT_POOL) -> list[DouyinPatternsSynthInputVideo]:
    return [_input_video(video_id=f"v{i}") for i in range(n)]


def _pattern_entry(rank: int, video_ids: list[str], **overrides) -> DouyinPatternEntry:
    base = {
        "rank": rank,
        "name_vn": f"Routine {rank} bước trước khi ngủ",
        "name_zh": "睡前仪式",
        "hook_template_vi": "3 việc trước khi ___ — 1 tháng sau bạn sẽ khác",
        "format_signal_vi": (
            "Quay POV cận cảnh, transition cắt nhanh sau mỗi 1.5s, voiceover thì thầm."
        ),
        "sample_video_ids": video_ids,
    }
    base.update(overrides)
    return DouyinPatternEntry(**base)


def _valid_synth(video_ids: list[str]) -> DouyinPatternsSynth:
    return DouyinPatternsSynth(
        patterns=[
            _pattern_entry(1, video_ids[:3]),
            _pattern_entry(2, video_ids[1:4]),
            _pattern_entry(3, video_ids[2:5]),
        ],
    )


# ── Pydantic validation ────────────────────────────────────────────


def test_pattern_entry_accepts_valid_payload() -> None:
    e = _pattern_entry(1, ["a", "b", "c"])
    assert e.rank == 1
    assert "___" in e.hook_template_vi


def test_pattern_entry_rejects_hook_without_blank() -> None:
    with pytest.raises(ValidationError, match="___"):
        _pattern_entry(1, ["a", "b"], hook_template_vi="3 việc trước khi ngủ")


def test_pattern_entry_rejects_duplicate_sample_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        _pattern_entry(1, ["a", "a", "b"])


def test_pattern_entry_rejects_too_few_sample_ids() -> None:
    with pytest.raises(ValidationError):
        _pattern_entry(1, ["a"])


def test_pattern_entry_rejects_too_many_sample_ids() -> None:
    with pytest.raises(ValidationError):
        _pattern_entry(1, ["a", "b", "c", "d", "e", "f"])


def test_pattern_entry_rejects_invalid_rank() -> None:
    with pytest.raises(ValidationError):
        _pattern_entry(4, ["a", "b"])


def test_synth_rejects_fewer_than_3_patterns() -> None:
    with pytest.raises(ValidationError):
        DouyinPatternsSynth(patterns=[_pattern_entry(1, ["a", "b"])])


def test_synth_rejects_more_than_3_patterns() -> None:
    with pytest.raises(ValidationError):
        DouyinPatternsSynth(patterns=[
            _pattern_entry(1, ["a", "b"]),
            _pattern_entry(2, ["c", "d"]),
            _pattern_entry(3, ["e", "f"]),
            _pattern_entry(1, ["g", "h"]),
        ])


def test_synth_rejects_duplicate_ranks() -> None:
    with pytest.raises(ValidationError, match="ranks"):
        DouyinPatternsSynth(patterns=[
            _pattern_entry(1, ["a", "b"]),
            _pattern_entry(1, ["c", "d"]),
            _pattern_entry(2, ["e", "f"]),
        ])


def test_synth_rejects_missing_rank() -> None:
    """Ranks must be exactly {1, 2, 3} — not {1, 1, 3} (rank 2 missing)."""
    with pytest.raises(ValidationError, match="ranks"):
        DouyinPatternsSynth(patterns=[
            _pattern_entry(1, ["a", "b"]),
            _pattern_entry(1, ["c", "d"]),
            _pattern_entry(3, ["e", "f"]),
        ])


# ── Public API ─────────────────────────────────────────────────────


def test_synth_returns_none_when_pool_below_min() -> None:
    out = synth_douyin_patterns(
        niche_name_vn="Wellness",
        niche_name_zh="养生",
        videos=_input_pool(MIN_INPUT_POOL - 1),
    )
    assert out is None


def test_synth_returns_gemini_output_on_happy_path() -> None:
    pool = _input_pool(MIN_INPUT_POOL)
    pool_ids = [v.video_id for v in pool]
    expected = _valid_synth(pool_ids)
    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        return_value=expected,
    ) as mock_call:
        out = synth_douyin_patterns(
            niche_name_vn="Sức khoẻ · Wellness",
            niche_name_zh="养生 · 健康生活",
            videos=pool,
        )
    assert out is expected
    _, kwargs = mock_call.call_args
    assert kwargs["niche_name_vn"] == "Sức khoẻ · Wellness"
    assert kwargs["niche_name_zh"] == "养生 · 健康生活"
    assert "videos_json" in kwargs
    assert "fingerprint" in kwargs


def test_synth_returns_none_when_gemini_raises() -> None:
    pool = _input_pool(MIN_INPUT_POOL)
    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        side_effect=RuntimeError("flash-preview 503"),
    ):
        out = synth_douyin_patterns(
            niche_name_vn="Wellness",
            niche_name_zh="养生",
            videos=pool,
        )
    assert out is None


def test_synth_returns_none_when_gemini_returns_out_of_pool_sample_id() -> None:
    """Hallucination guard — Gemini fabricates a video_id outside the
    input pool → orchestrator skips the (niche, week) batch."""
    pool = _input_pool(MIN_INPUT_POOL)
    pool_ids = [v.video_id for v in pool]
    bogus_synth = DouyinPatternsSynth(patterns=[
        _pattern_entry(1, pool_ids[:3]),
        _pattern_entry(2, [pool_ids[1], pool_ids[2], "fabricated_xyz"]),
        _pattern_entry(3, pool_ids[2:5]),
    ])
    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        return_value=bogus_synth,
    ):
        out = synth_douyin_patterns(
            niche_name_vn="Wellness",
            niche_name_zh="养生",
            videos=pool,
        )
    assert out is None


def test_synth_passes_compact_json_with_short_keys() -> None:
    """The serialised pool uses short keys (id/zh/vi/hook/...) to keep
    the input token cost down."""
    pool = _input_pool(MIN_INPUT_POOL)
    pool_ids = [v.video_id for v in pool]
    expected = _valid_synth(pool_ids)
    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        return_value=expected,
    ) as mock_call:
        synth_douyin_patterns(
            niche_name_vn="Wellness",
            niche_name_zh="养生",
            videos=pool,
        )
    payload = mock_call.call_args.kwargs["videos_json"]
    rows = json.loads(payload)
    assert len(rows) == MIN_INPUT_POOL
    assert set(rows[0].keys()) == {
        "id", "zh", "vi", "hook", "hook_type", "format", "views", "rise",
    }


# ── lru_cache behaviour ────────────────────────────────────────────


def test_inner_call_is_cached_across_repeated_inputs() -> None:
    """Patches one layer DEEPER than _call_patterns_gemini so the
    lru_cache is actually exercised. Mirrors the D2a / D3a pattern."""
    pool = _input_pool(MIN_INPUT_POOL)
    pool_ids = [v.video_id for v in pool]
    expected = _valid_synth(pool_ids)
    fake_response = MagicMock()
    response_text = expected.model_dump_json()

    with (
        patch(
            "getviews_pipeline.gemini._generate_content_models",
            return_value=fake_response,
        ) as gen_mock,
        patch(
            "getviews_pipeline.gemini._response_text",
            return_value=response_text,
        ) as text_mock,
    ):
        # First call — should hit Gemini.
        out1 = synth_douyin_patterns(
            niche_name_vn="Wellness", niche_name_zh="养生", videos=pool,
        )
        # Second call with identical inputs — should hit the cache.
        out2 = synth_douyin_patterns(
            niche_name_vn="Wellness", niche_name_zh="养生", videos=pool,
        )

    assert out1 is not None and out2 is not None
    assert out1.model_dump() == out2.model_dump()
    # _generate_content_models called ONCE — the second invocation hit
    # the lru_cache.
    assert gen_mock.call_count == 1
    assert text_mock.call_count == 1


def test_fingerprint_changes_when_a_video_views_changes() -> None:
    """Different input pools must produce different cache keys —
    otherwise stale Gemini output would leak across weeks."""
    pool_a = _input_pool(MIN_INPUT_POOL)
    pool_b = _input_pool(MIN_INPUT_POOL)
    pool_b[0] = _input_video(video_id="v0", views=999_999_999)
    pool_a_ids = [v.video_id for v in pool_a]
    expected_a = _valid_synth(pool_a_ids)
    expected_b = _valid_synth(pool_a_ids)

    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        side_effect=[expected_a, expected_b],
    ) as mock_call:
        synth_douyin_patterns(
            niche_name_vn="Wellness", niche_name_zh="养生", videos=pool_a,
        )
        synth_douyin_patterns(
            niche_name_vn="Wellness", niche_name_zh="养生", videos=pool_b,
        )

    fp_a = mock_call.call_args_list[0].kwargs["fingerprint"]
    fp_b = mock_call.call_args_list[1].kwargs["fingerprint"]
    assert fp_a != fp_b


def test_synth_passes_input_pool_videos_json_to_gemini() -> None:
    """The full pool (post-trim) reaches the Gemini layer as JSON."""
    pool = _input_pool(MIN_INPUT_POOL)
    pool_ids = [v.video_id for v in pool]
    expected = _valid_synth(pool_ids)
    with patch(
        "getviews_pipeline.douyin_patterns_synth._call_patterns_gemini",
        return_value=expected,
    ) as mock_call:
        synth_douyin_patterns(
            niche_name_vn="Wellness", niche_name_zh="养生", videos=pool,
        )
    payload = json.loads(mock_call.call_args.kwargs["videos_json"])
    assert {row["id"] for row in payload} == set(pool_ids)
