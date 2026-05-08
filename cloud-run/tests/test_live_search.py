"""Unit tests for live_search keyword supplement helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from getviews_pipeline.live_search import (
    derive_search_terms,
    fetch_live_supplement,
    format_live_awemes_for_prompt,
    needs_live_search,
)


def test_needs_live_search_thin_corpus() -> None:
    assert needs_live_search("", 10) is True
    assert needs_live_search("x", 49) is True
    assert needs_live_search("x", 50) is False


def test_needs_live_search_recency_query() -> None:
    assert needs_live_search("Xu hướng đang viral trong tuần này", 1000) is True
    assert needs_live_search("trending sound 7 ngày", 200) is True
    assert needs_live_search("hook tĩnh lặng", 200) is False


def test_derive_search_terms_caps() -> None:
    terms = derive_search_terms("Skincare", ["bold_claim", "before_after"], "q")
    assert len(terms) <= 3
    assert any("skincare" in t.lower() for t in terms)


def test_format_live_awemes_for_prompt_empty() -> None:
    assert format_live_awemes_for_prompt([]) == ""


def test_format_live_awemes_for_prompt_shapes() -> None:
    aw = [
        {
            "desc": "Hello world",
            "author": {"unique_id": "foo"},
            "statistics": {"play_count": 1200},
        }
    ]
    s = format_live_awemes_for_prompt(aw)
    assert "@foo" in s
    assert "1,200" in s
    assert "Hello" in s


# ── Audit fix #1 — blocklist applied to live ED keyword search ────────────


def _aweme(handle: str, aweme_id: str = "1", views: int = 1000) -> dict[str, Any]:
    return {
        "aweme_id": aweme_id,
        "desc": "x",
        "author": {"unique_id": handle},
        "statistics": {"play_count": views},
    }


@pytest.mark.asyncio
async def test_fetch_live_supplement_filters_blocklisted_handles() -> None:
    """Sprint 8.5 blocklist must filter the live ED keyword path too —
    otherwise theanh28*/kenh14*/24h.* leak into the Pattern + Ideas
    prompt, undoing the corpus cleanup."""
    fake_results = (
        [
            _aweme("kenh14official", "1"),       # blocklisted
            _aweme("legit_creator", "2"),
            _aweme("theanh28sport", "3"),        # blocklisted
            _aweme("another_real_creator", "4"),
        ],
        None,
    )
    with patch(
        "getviews_pipeline.live_search.fetch_keyword_search",
        AsyncMock(return_value=fake_results),
    ):
        out = await fetch_live_supplement(
            query="đang viral tuần này",
            niche_label="Skincare",
            top_hook_types=["bold_claim"],
            corpus_count=10,  # forces needs_live_search to True
        )
    handles = [(a.get("author") or {}).get("unique_id") for a in out]
    assert "kenh14official" not in handles
    assert "theanh28sport" not in handles
    assert "legit_creator" in handles
    assert "another_real_creator" in handles


@pytest.mark.asyncio
async def test_fetch_live_supplement_returns_empty_when_not_needed() -> None:
    """Cheap-path guard: when corpus is dense and query lacks recency
    signals, ED should not be hit at all."""
    with patch(
        "getviews_pipeline.live_search.fetch_keyword_search",
        AsyncMock(return_value=([], None)),
    ) as mock_fetch:
        out = await fetch_live_supplement(
            query="hook tĩnh lặng",        # no recency signal
            niche_label="Skincare",
            top_hook_types=["bold_claim"],
            corpus_count=200,                # above THIN_CORPUS_THRESHOLD
        )
    assert out == []
    mock_fetch.assert_not_called()
