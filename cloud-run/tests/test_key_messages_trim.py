"""W5-3 — key_messages trimmed from extraction schema."""

from __future__ import annotations

from getviews_pipeline.models import VideoAnalysis


def test_video_analysis_schema_omits_key_messages() -> None:
    props = VideoAnalysis.model_json_schema().get("properties") or {}
    assert "key_messages" not in props
