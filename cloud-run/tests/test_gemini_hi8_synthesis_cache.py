"""HI-8 — synthesis path: per-model context cache + system_instruction fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from google.genai import types

from getviews_pipeline.gemini import _apply_synthesis_context_for_model


def test_synthesis_fallback_system_instruction_when_cache_disabled() -> None:
    client = MagicMock()
    base = types.GenerateContentConfig(temperature=0.8, max_output_tokens=100)
    with patch("getviews_pipeline.gemini.GEMINI_SYNTHESIS_CONTEXT_CACHE", False):
        cfg = _apply_synthesis_context_for_model(
            client,
            base,
            kind="diag_v2",
            model="gemini-3.1-flash-lite",
            system_text="STATIC_SYS",
        )
    assert cfg.system_instruction == "STATIC_SYS"
    assert cfg.cached_content is None
    assert cfg.temperature == 0.8


def test_synthesis_uses_cached_content_when_resolved() -> None:
    client = MagicMock()
    base = types.GenerateContentConfig(temperature=0.8, max_output_tokens=100)
    with patch("getviews_pipeline.gemini.GEMINI_SYNTHESIS_CONTEXT_CACHE", True):
        with patch(
            "getviews_pipeline.gemini._get_synthesis_cached_content_name",
            return_value="cachedContents/xyz",
        ):
            cfg = _apply_synthesis_context_for_model(
                client,
                base,
                kind="intent_markdown",
                model="gemini-3.1-flash-lite",
                system_text="SYS",
            )
    assert cfg.cached_content == "cachedContents/xyz"
    assert cfg.system_instruction is None
