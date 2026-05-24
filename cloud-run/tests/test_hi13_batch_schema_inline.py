"""HI-13 — batch JSON schema must inline ``$ref`` (Batch API rejects unresolved refs)."""

from __future__ import annotations

from getviews_pipeline.gemini import _inline_json_schema_defs
from getviews_pipeline.models import VideoAnalysis


def test_inline_json_schema_defs_resolves_hook_analysis_ref() -> None:
    schema = VideoAnalysis.model_json_schema()
    assert "$ref" in str(schema.get("properties", {}).get("hook_analysis", {}))

    inlined = _inline_json_schema_defs(schema)
    hook = (inlined.get("properties") or {}).get("hook_analysis")
    assert isinstance(hook, dict)
    assert "$ref" not in hook
    assert "properties" in hook
    assert "$defs" not in inlined
