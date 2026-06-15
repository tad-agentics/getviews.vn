"""resolve_embedded_tiles caption_snippet — sanitize before truncate."""

from __future__ import annotations

from getviews_pipeline.analysis_guards import TRANSCRIPT_UNAVAILABLE_MARKER
from getviews_pipeline.diagnose_parse import resolve_embedded_tiles


def test_resolve_embedded_tiles_strips_marker_before_truncating_caption() -> None:
    marker = TRANSCRIPT_UNAVAILABLE_MARKER
    tail = "A" * 250
    refs = [
        {
            "aweme_id": "111",
            "desc": f"{marker} {tail}",
            "views": 12_000,
        },
    ]
    out = resolve_embedded_tiles([{"aweme_id": "111"}], refs)
    snippet = out[0]["caption_snippet"]
    assert "Transcript không khả dụng" not in snippet
    assert len(snippet) == 200
    assert snippet == tail[:200]
