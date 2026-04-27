"""M2 — explicit safety_settings on Gemini calls.

Three things to lock down so we don't drift back to the SDK default:

  1. ``_default_safety_settings()`` covers all four harm categories at
     BLOCK_ONLY_HIGH.
  2. ``_ensure_safety_settings()`` injects defaults when the caller
     didn't supply any, on both ``None`` and bare ``GenerateContentConfig``.
  3. Caller-provided safety settings are NEVER overwritten — if a
     specific call site wants stricter blocking, we honour it.
"""

from __future__ import annotations

import pytest

pytest.importorskip("google.genai")

from google.genai import types  # noqa: E402  (after importorskip)

from getviews_pipeline.gemini import (  # noqa: E402
    _default_safety_settings,
    _ensure_safety_settings,
)


def test_default_safety_settings_covers_four_harm_categories() -> None:
    settings = _default_safety_settings()
    cats = {s.category for s in settings}
    assert types.HarmCategory.HARM_CATEGORY_HARASSMENT in cats
    assert types.HarmCategory.HARM_CATEGORY_HATE_SPEECH in cats
    assert types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in cats
    assert types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in cats


def test_default_safety_settings_use_block_only_high() -> None:
    """Vietnamese creator content (drinking, dating, finance hooks) gets
    over-flagged at BLOCK_MEDIUM_AND_ABOVE; stick with BLOCK_ONLY_HIGH."""
    settings = _default_safety_settings()
    for s in settings:
        assert s.threshold == types.HarmBlockThreshold.BLOCK_ONLY_HIGH


def test_ensure_injects_defaults_when_config_is_none() -> None:
    out = _ensure_safety_settings(None)
    assert out is not None
    assert out.safety_settings is not None
    assert len(out.safety_settings) == 4


def test_ensure_injects_defaults_into_bare_config() -> None:
    bare = types.GenerateContentConfig(temperature=0.2)
    out = _ensure_safety_settings(bare)
    assert out.safety_settings is not None
    assert len(out.safety_settings) == 4
    # Caller's other knobs must survive the copy.
    assert out.temperature == 0.2


def test_ensure_does_not_overwrite_caller_safety_settings() -> None:
    """If a call site has thought hard about its safety profile we leave
    it alone — operator intent beats the dispatcher default."""
    custom = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        ),
    ]
    cfg = types.GenerateContentConfig(safety_settings=custom)
    out = _ensure_safety_settings(cfg)
    assert out.safety_settings == custom
