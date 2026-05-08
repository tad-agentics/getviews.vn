"""Unit tests for ``_resolve_actual_niche_from_content`` (Sprint 9).

Pure logic — no Supabase or EnsembleData. Pins the ≥2-hit margin rule that
stops the keyword-pool loop niche from overwriting a clearly different
vertical in ``video_corpus.niche_id``.
"""

from __future__ import annotations

import pytest


def _f():
    try:
        from getviews_pipeline.corpus_ingest import _resolve_actual_niche_from_content
        return _resolve_actual_niche_from_content
    except ModuleNotFoundError:
        pytest.skip("getviews_pipeline not on path or deps missing")


def test_keeps_default_when_no_other_niche_dominates() -> None:
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine"],
        3: ["#outfit", "#thoitrang"],
    }
    assert (
        resolve(
            {"analysis": {"topics": [], "hook_analysis": {"hook_phrase": ""}}},
            "xin chào đây là caption không liên quan hashtag tín hiệu",
            mp,
            2,
        )
        == 2
    )


def test_reassigns_to_dominant_niche_when_signal_is_strong() -> None:
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine"],
        3: ["#outfit", "#OOTD", "#thoitrang"],
    }
    caption = (
        "looks tuần lễ thời trang #outfit #OOTD #thoitrang "
        "red carpet energy"
    )
    assert resolve({"analysis": {}}, caption, mp, default_niche_id=2) == 3


def test_requires_at_least_2_more_hits_to_reassign() -> None:
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine"],
        3: ["#outfit", "#thoitrang", "#streetstyle"],
    }
    # 1 skincare hit, 2 fashion hits → margin 1 < 2 → keep default 2
    caption = "vừa skincare vừa #skincare daily nhưng cũng #outfit #thoitrang"
    assert resolve({"analysis": {}}, caption, mp, default_niche_id=2) == 2


def test_resilient_to_missing_caption_or_analysis() -> None:
    resolve = _f()
    mp = {2: ["#a"], 3: ["#b"]}
    assert resolve(None, None, mp, 3) == 3
    assert resolve({}, "", mp, 2) == 2
