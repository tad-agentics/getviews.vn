"""D2a (2026-06-03) — Chinese → Vietnamese translator tests.

Mocks ``_call_translation_gemini`` so tests don't hit the network. Each
case targets one slice of the public surface:
  • Public API contract (returns CaptionTranslation or None).
  • Noise-strip behaviour (mentions, URLs, whitespace).
  • lru_cache de-dupe (repeated captions don't re-call Gemini).
  • Error path — Gemini raises → public API returns None.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from getviews_pipeline.douyin_translator import (
    CaptionTranslation,
    _reset_cache_for_tests,
    _strip_caption_noise,
    translate_douyin_caption,
)


# ── Fixture: reset the lru_cache between cases so each test starts clean.


@pytest.fixture(autouse=True)
def _clear_cache_between_tests() -> None:
    _reset_cache_for_tests()


# ── Noise-strip ─────────────────────────────────────────────────────


def test_strip_drops_at_mentions_keeps_hashtags() -> None:
    """Hashtags carry semantic content — keep them so Gemini gets the
    extra context. @mentions don't help translation."""
    out = _strip_caption_noise("睡前3件事 @sleepwell.life #养生 改变人生")
    assert "@sleepwell" not in out
    assert "#养生" in out
    assert "睡前3件事" in out


def test_strip_drops_urls() -> None:
    out = _strip_caption_noise("看完这个 https://v.douyin.com/abc123 你就懂了")
    assert "https://" not in out
    assert "看完这个" in out


def test_strip_collapses_whitespace() -> None:
    out = _strip_caption_noise("一  两\n\n三\t四")
    # Single space between every token, no leading/trailing whitespace.
    assert out == "一 两 三 四"


def test_strip_handles_cjk_at_mentions() -> None:
    """@用户名 with Chinese characters should also strip."""
    out = _strip_caption_noise("一起来看 @抖音用户 测评")
    assert "@抖音用户" not in out
    assert "一起来看" in out
    assert "测评" in out


# ── Public API ─────────────────────────────────────────────────────


def test_translate_returns_none_on_empty_input() -> None:
    assert translate_douyin_caption("") is None
    assert translate_douyin_caption("   ") is None
    assert translate_douyin_caption(None) is None  # type: ignore[arg-type]


def test_translate_returns_none_when_caption_is_only_noise() -> None:
    """Caption that's nothing but @mentions + URLs should return None
    (no real content to translate)."""
    assert translate_douyin_caption("@user @other https://link") is None


def test_translate_calls_gemini_and_returns_translation() -> None:
    expected = CaptionTranslation(
        title_vi="Trước khi ngủ làm 3 việc này",
        sub_vi="3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",
    )
    with patch(
        "getviews_pipeline.douyin_translator._call_translation_gemini",
        return_value=expected,
    ) as mock_call:
        out = translate_douyin_caption("睡前3件事 改变人生", creator_handle="sleepwell.life")
    assert out == expected
    # Noise-stripped caption + handle reach the Gemini call.
    args, _ = mock_call.call_args
    assert args[0] == "睡前3件事 改变人生"
    assert args[1] == "sleepwell.life"


def test_translate_passes_empty_handle_when_omitted() -> None:
    """``creator_handle=None`` should reach the Gemini call as ``""``
    (the prompt branches on truthiness to skip the handle line)."""
    expected = CaptionTranslation(title_vi="X", sub_vi="X")
    with patch(
        "getviews_pipeline.douyin_translator._call_translation_gemini",
        return_value=expected,
    ) as mock_call:
        translate_douyin_caption("睡前3件事")
    args, _ = mock_call.call_args
    assert args[1] == ""


def test_translate_returns_none_when_gemini_raises() -> None:
    """Network / Pydantic-validation failures must NOT crash the ingest
    — caller lands the row with ``title_vi=NULL`` and D3 synth retries."""
    with patch(
        "getviews_pipeline.douyin_translator._call_translation_gemini",
        side_effect=RuntimeError("flash-preview 503"),
    ):
        out = translate_douyin_caption("睡前3件事", creator_handle="x")
    assert out is None


# ── lru_cache ─────────────────────────────────────────────────────
# These tests target the lru_cache one layer DEEPER (patching
# ``_generate_content_models`` instead of ``_call_translation_gemini``)
# so the cache itself is exercised, not bypassed.


def test_lru_cache_dedupes_identical_captions() -> None:
    """Same caption + handle twice → only one underlying Gemini call.
    Trending captions repeat across the candidate pool so the cache is
    meaningful inside a single batch run."""
    fake_response_json = '{"title_vi": "X", "sub_vi": "X"}'
    with patch(
        "getviews_pipeline.gemini._generate_content_models",
        return_value=object(),
    ), patch(
        "getviews_pipeline.gemini._response_text",
        return_value=fake_response_json,
    ) as mock_text:
        a = translate_douyin_caption("睡前3件事 改变人生", creator_handle="alice")
        b = translate_douyin_caption("睡前3件事 改变人生", creator_handle="alice")
    assert a == b
    assert isinstance(a, CaptionTranslation)
    # Cache hit on second call → only one Gemini round-trip happened.
    assert mock_text.call_count == 1


def test_lru_cache_keys_on_handle() -> None:
    """Same caption + DIFFERENT handles → two separate Gemini calls
    (handle appears in the prompt and may sway translation of named
    entities)."""
    fake_response_json = '{"title_vi": "X", "sub_vi": "X"}'
    with patch(
        "getviews_pipeline.gemini._generate_content_models",
        return_value=object(),
    ), patch(
        "getviews_pipeline.gemini._response_text",
        return_value=fake_response_json,
    ) as mock_text:
        translate_douyin_caption("睡前3件事 改变人生", creator_handle="alice")
        translate_douyin_caption("睡前3件事 改变人生", creator_handle="bob")
    assert mock_text.call_count == 2


# ── Pydantic validation ──────────────────────────────────────────


def test_caption_translation_model_enforces_length_caps() -> None:
    from pydantic import ValidationError

    # Empty title_vi rejected.
    with pytest.raises(ValidationError):
        CaptionTranslation(title_vi="", sub_vi="X")
    # Empty sub_vi rejected.
    with pytest.raises(ValidationError):
        CaptionTranslation(title_vi="X", sub_vi="")
    # sub_vi too long rejected (cap = 120).
    with pytest.raises(ValidationError):
        CaptionTranslation(title_vi="X", sub_vi="x" * 121)
    # title_vi too long rejected (cap = 400).
    with pytest.raises(ValidationError):
        CaptionTranslation(title_vi="x" * 401, sub_vi="X")
