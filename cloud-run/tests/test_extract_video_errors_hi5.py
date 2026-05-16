"""HI-5 — extract_video_errors uses extraction tier + thinking_budget=0 + call_site."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline.services.extraction import extract_video_errors


def test_extract_video_errors_hi5_model_fallbacks_call_site_thinking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_generate(
        contents: object,
        *,
        primary_model: str,
        fallbacks: list[str],
        config: object,
        call_site: str = "unknown",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> MagicMock:
        captured["primary_model"] = primary_model
        captured["fallbacks"] = fallbacks
        captured["call_site"] = call_site
        captured["config"] = config
        out = MagicMock()
        out.text = '{"errors": []}'
        return out

    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models",
        fake_generate,
    )

    err_list = extract_video_errors(
        extraction_mode="win",
        video={
            "creator_handle": "x",
            "views": 1000,
            "engagement_rate": 0.05,
            "content_format": "talk",
        },
        analysis={"hook_analysis": {"hook_phrase": "test"}},
        niche_label="Beauty",
        niche_row={"avg_views": 5000, "avg_retention": 0.4, "sample_size": 100},
        retention_curve=None,
    )
    assert err_list == []
    assert captured["primary_model"] == gv_config.GEMINI_EXTRACTION_MODEL
    assert captured["fallbacks"] == gv_config.GEMINI_EXTRACTION_FALLBACKS
    assert captured["call_site"] == "extract_video_errors"
    cfg = captured["config"]
    tc = getattr(cfg, "thinking_config", None)
    assert tc is not None
    assert getattr(tc, "thinking_budget", object()) == 0
