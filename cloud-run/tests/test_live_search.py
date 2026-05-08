"""Unit tests for live_search keyword supplement helpers."""

from __future__ import annotations

from getviews_pipeline.live_search import (
    derive_search_terms,
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
