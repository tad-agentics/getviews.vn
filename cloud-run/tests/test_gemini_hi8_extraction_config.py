"""HI-8 — extraction uses system_instruction (+ optional context cache)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from getviews_pipeline.gemini import _configure_extraction_generate_config


def test_extraction_config_sets_system_instruction_when_cache_off() -> None:
    client = MagicMock()
    schema = {"type": "object", "properties": {}}
    sys_text = "STATIC_SYSTEM_BLOCK_FOR_TESTS"
    with patch("getviews_pipeline.gemini._get_extraction_cached_content_name", return_value=None):
        cfg = _configure_extraction_generate_config(
            client,
            schema,
            kind="video",
            system_text=sys_text,
        )
    assert cfg.system_instruction == sys_text
    assert cfg.cached_content is None
    assert cfg.response_mime_type == "application/json"


def test_extraction_config_uses_cached_content_when_available() -> None:
    client = MagicMock()
    schema = {"type": "object"}
    with patch(
        "getviews_pipeline.gemini._get_extraction_cached_content_name",
        return_value="cachedContents/abc123",
    ):
        cfg = _configure_extraction_generate_config(
            client,
            schema,
            kind="video",
            system_text="x",
        )
    assert cfg.cached_content == "cachedContents/abc123"
