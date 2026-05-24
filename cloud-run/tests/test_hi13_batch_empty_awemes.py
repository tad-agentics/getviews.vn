"""HI-13 — empty aweme list must return ``([], {})`` for tuple unpack sites."""

from __future__ import annotations

import asyncio

from getviews_pipeline.corpus_ingest import _analyze_videos_gemini_batch_for_corpus


def test_analyze_videos_gemini_batch_empty_returns_tuple() -> None:
    results, batch_out = asyncio.run(
        _analyze_videos_gemini_batch_for_corpus("test-niche", []),
    )
    assert results == []
    assert batch_out == {}
