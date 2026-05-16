"""HI-8 — synthesis path: per-model context cache + system_instruction fallback."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from google.genai import types

from getviews_pipeline.gemini import _apply_synthesis_context_for_model, _generate_content_models


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


def test_generate_content_models_applies_system_instruction_when_cache_env_off() -> None:
    """Regression: synthesis_cache_* must merge even when Phase B cache is disabled.

    ``GEMINI_SYNTHESIS_CONTEXT_CACHE`` only gates ``client.caches.create``;
    ``synthesis_cache_system_text`` must still become ``system_instruction``.
    """
    mock_client = MagicMock()
    mock_meta = MagicMock(prompt_token_count=1, candidates_token_count=1)
    mock_resp = MagicMock(usage_metadata=mock_meta)
    mock_client.models.generate_content.return_value = mock_resp

    with (
        patch("getviews_pipeline.gemini._get_client", return_value=mock_client),
        patch("getviews_pipeline.gemini.GEMINI_SYNTHESIS_CONTEXT_CACHE", False),
        patch("getviews_pipeline.gemini_cost.check_gemini_daily_budget"),
        patch("getviews_pipeline.gemini_cost.log_gemini_call"),
        patch("getviews_pipeline.telemetry.span", return_value=nullcontext()),
    ):
        _generate_content_models(
            ["user turn"],
            primary_model="gemini-3.1-flash-lite",
            fallbacks=[],
            config=types.GenerateContentConfig(temperature=0.3),
            call_site="test_synth_sys_inst",
            synthesis_cache_kind="diag_v1",
            synthesis_cache_system_text="VOICE_DOMAIN_STATIC",
        )

    kw = mock_client.models.generate_content.call_args.kwargs
    assert kw["config"].system_instruction == "VOICE_DOMAIN_STATIC"
    assert kw["config"].cached_content is None
    assert kw["config"].temperature == 0.3
