"""D3a (2026-06-04) — Kho Douyin · adapt-synth tests.

Mocks ``_call_synth_gemini`` so tests don't hit the network. Each
test exercises one slice of the public surface:
  • Public API contract (returns DouyinAdaptSynth or None).
  • Pydantic validation (eta range ordering, tag enum, length caps).
  • Error path — Gemini raises → public API returns None.
  • lru_cache behaviour at the inner Gemini-call layer.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from getviews_pipeline.douyin_synth import (
    DouyinAdaptSynth,
    TranslatorNote,
    _reset_cache_for_tests,
    synth_douyin_adapt,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests() -> None:
    _reset_cache_for_tests()


def _valid_synth(**overrides) -> DouyinAdaptSynth:
    base = {
        "adapt_level": "green",
        "adapt_reason": "Wellness routine ngắn, không phụ thuộc văn hoá CN.",
        "eta_weeks_min": 2,
        "eta_weeks_max": 4,
        "sub_vi": "3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",
        "translator_notes": [
            {"tag": "TỪ NGỮ", "note": "睡前 = trước khi ngủ. VN dùng tự nhiên hơn 'tối nào cũng'."},
            {"tag": "NHẠC NỀN", "note": "Bản gốc dùng remix Jay Chou; VN nên dùng piano slow để tránh copyright."},
        ],
    }
    base.update(overrides)
    return DouyinAdaptSynth(**base)


# ── Pydantic validation ────────────────────────────────────────────


def test_synth_accepts_valid_payload() -> None:
    s = _valid_synth()
    assert s.adapt_level == "green"
    assert len(s.translator_notes) == 2


def test_synth_rejects_invalid_adapt_level() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(adapt_level="purple")  # not a literal


def test_synth_rejects_eta_max_less_than_min() -> None:
    with pytest.raises(ValidationError, match="eta_weeks_max"):
        _valid_synth(eta_weeks_min=5, eta_weeks_max=3)


def test_synth_rejects_eta_above_52_weeks() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(eta_weeks_max=99)


def test_synth_rejects_eta_below_1_week() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(eta_weeks_min=0, eta_weeks_max=2)


def test_synth_rejects_too_short_adapt_reason() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(adapt_reason="ngắn")


def test_synth_rejects_too_long_adapt_reason() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(adapt_reason="x" * 201)


def test_synth_rejects_too_short_sub_vi() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(sub_vi="x")


def test_synth_rejects_too_long_sub_vi() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(sub_vi="x" * 121)


def test_synth_rejects_only_one_note() -> None:
    """Must have at least 2 notes."""
    with pytest.raises(ValidationError):
        _valid_synth(translator_notes=[
            {"tag": "TỪ NGỮ", "note": "Một note duy nhất, chưa đủ."},
        ])


def test_synth_rejects_more_than_5_notes() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(translator_notes=[
            {"tag": "TỪ NGỮ", "note": f"Note {i} mock content for test."}
            for i in range(6)
        ])


def test_synth_rejects_unknown_translator_note_tag() -> None:
    with pytest.raises(ValidationError):
        _valid_synth(translator_notes=[
            {"tag": "RANDOM_TAG", "note": "Tag không tồn tại trong enum."},
            {"tag": "TỪ NGỮ", "note": "Note hợp lệ."},
        ])


def test_translator_note_rejects_too_short_note() -> None:
    """Notes must be ≥ 12 chars to avoid 'có thể adapt' filler."""
    with pytest.raises(ValidationError):
        TranslatorNote(tag="TỪ NGỮ", note="ngắn")


# ── Public API: synth_douyin_adapt ─────────────────────────────────


def test_synth_returns_none_on_empty_title_zh() -> None:
    out = synth_douyin_adapt(
        title_zh="",
        title_vi="",
        hook_phrase=None,
        hook_type=None,
        niche_name_vn="Wellness",
        niche_name_zh="养生",
    )
    assert out is None


def test_synth_returns_none_on_whitespace_title() -> None:
    out = synth_douyin_adapt(
        title_zh="   \n\t",
        title_vi=None,
        hook_phrase=None,
        hook_type=None,
        niche_name_vn="Wellness",
        niche_name_zh="养生",
    )
    assert out is None


def test_synth_returns_gemini_output_on_happy_path() -> None:
    expected = _valid_synth()
    with patch(
        "getviews_pipeline.douyin_synth._call_synth_gemini",
        return_value=expected,
    ) as mock_call:
        out = synth_douyin_adapt(
            title_zh="睡前3件事 改变人生",
            title_vi="3 việc trước khi ngủ",
            hook_phrase="睡前3件事",
            hook_type="curiosity_gap",
            niche_name_vn="Sức khoẻ · Wellness",
            niche_name_zh="养生 · 健康生活",
        )
    assert out is expected
    # Inputs reach the Gemini call as kwargs (lru_cache-friendly).
    _, kwargs = mock_call.call_args
    assert kwargs["title_zh"] == "睡前3件事 改变人生"
    assert kwargs["title_vi"] == "3 việc trước khi ngủ"
    assert kwargs["hook_type"] == "curiosity_gap"


def test_synth_returns_none_when_gemini_raises() -> None:
    """Network / Pydantic-validation failures must NOT crash the D3b
    orchestrator — caller skips and re-attempts on next cron run."""
    with patch(
        "getviews_pipeline.douyin_synth._call_synth_gemini",
        side_effect=RuntimeError("flash-preview 503"),
    ):
        out = synth_douyin_adapt(
            title_zh="睡前3件事",
            title_vi=None,
            hook_phrase=None,
            hook_type=None,
            niche_name_vn="Wellness",
            niche_name_zh="养生",
        )
    assert out is None


def test_synth_passes_empty_strings_for_missing_optional_fields() -> None:
    """When hook_phrase / hook_type / title_vi are None, the Gemini
    call gets ``""`` (lru_cache-friendly hashable args; the prompt
    handles empty strings explicitly)."""
    expected = _valid_synth()
    with patch(
        "getviews_pipeline.douyin_synth._call_synth_gemini",
        return_value=expected,
    ) as mock_call:
        synth_douyin_adapt(
            title_zh="睡前3件事",
            title_vi=None,
            hook_phrase=None,
            hook_type=None,
            niche_name_vn="Wellness",
            niche_name_zh="养生",
        )
    _, kwargs = mock_call.call_args
    assert kwargs["title_vi"] == ""
    assert kwargs["hook_phrase"] == ""
    assert kwargs["hook_type"] == ""


# ── lru_cache (one layer deeper to actually exercise the cache) ────


def test_lru_cache_dedupes_identical_inputs() -> None:
    """Same input twice → underlying Gemini round-trip happens once.
    Trending captions repeat across the candidate pool so the cache is
    meaningful inside a single batch run."""
    fake_response_json = (
        '{"adapt_level": "green",'
        ' "adapt_reason": "Wellness universal, không phụ thuộc CN.",'
        ' "eta_weeks_min": 2, "eta_weeks_max": 4,'
        ' "sub_vi": "3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",'
        ' "translator_notes": ['
        '   {"tag": "TỪ NGỮ", "note": "睡前 = trước khi ngủ, dùng tự nhiên hơn."},'
        '   {"tag": "NHẠC NỀN", "note": "Đổi remix Jay Chou sang piano slow VN."}'
        ' ]}'
    )
    with patch(
        "getviews_pipeline.gemini._generate_content_models",
        return_value=object(),
    ), patch(
        "getviews_pipeline.gemini._response_text",
        return_value=fake_response_json,
    ) as mock_text:
        a = synth_douyin_adapt(
            title_zh="睡前3件事",
            title_vi="3 việc trước khi ngủ",
            hook_phrase=None,
            hook_type=None,
            niche_name_vn="Wellness",
            niche_name_zh="养生",
        )
        b = synth_douyin_adapt(
            title_zh="睡前3件事",
            title_vi="3 việc trước khi ngủ",
            hook_phrase=None,
            hook_type=None,
            niche_name_vn="Wellness",
            niche_name_zh="养生",
        )
    assert a == b
    assert isinstance(a, DouyinAdaptSynth)
    # Cache hit on second call → only one Gemini round-trip happened.
    assert mock_text.call_count == 1


def test_lru_cache_distinguishes_titles_within_same_niche() -> None:
    """Different captions in the same niche must trigger two Gemini
    calls (not collapsed to one cache slot)."""
    fake_response_json = (
        '{"adapt_level": "green",'
        ' "adapt_reason": "Test response, không phụ thuộc CN.",'
        ' "eta_weeks_min": 1, "eta_weeks_max": 4,'
        ' "sub_vi": "Sub gloss tiếng Việt cho thẻ video",'
        ' "translator_notes": ['
        '   {"tag": "TỪ NGỮ", "note": "Note placeholder để pass min length."},'
        '   {"tag": "NHẠC NỀN", "note": "Đổi nhạc CN sang nhạc Việt cho phù hợp."}'
        ' ]}'
    )
    with patch(
        "getviews_pipeline.gemini._generate_content_models",
        return_value=object(),
    ), patch(
        "getviews_pipeline.gemini._response_text",
        return_value=fake_response_json,
    ) as mock_text:
        synth_douyin_adapt(
            title_zh="睡前3件事",
            title_vi="3 việc trước khi ngủ",
            hook_phrase=None, hook_type=None,
            niche_name_vn="Wellness", niche_name_zh="养生",
        )
        synth_douyin_adapt(
            title_zh="早起5分钟",
            title_vi="Dậy sớm 5 phút",
            hook_phrase=None, hook_type=None,
            niche_name_vn="Wellness", niche_name_zh="养生",
        )
    assert mock_text.call_count == 2
