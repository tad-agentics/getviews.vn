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


# Audit Pass-2 fix #7 — resolver now returns ``(resolved_nid, hits_map)``
# instead of just ``int``. Tests unpack the tuple.


def test_keeps_default_when_no_other_niche_dominates() -> None:
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine"],
        3: ["#outfit", "#thoitrang"],
    }
    nid, _hits = resolve(
        {"analysis": {"topics": [], "hook_analysis": {"hook_phrase": ""}}},
        "xin chào đây là caption không liên quan hashtag tín hiệu",
        mp,
        2,
    )
    assert nid == 2


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
    nid, hits = resolve({"analysis": {}}, caption, mp, default_niche_id=2)
    assert nid == 3
    # Audit Pass-2 fix #7 — caller can read the per-niche counts
    # without re-running the haystack computation.
    assert hits[3] >= hits[2] + 2


def test_requires_at_least_2_more_hits_to_reassign() -> None:
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine"],
        3: ["#outfit", "#thoitrang", "#streetstyle"],
    }
    # 1 skincare hit, 2 fashion hits → margin 1 < 2 → keep default 2
    caption = "vừa skincare vừa #skincare daily nhưng cũng #outfit #thoitrang"
    nid, _hits = resolve({"analysis": {}}, caption, mp, default_niche_id=2)
    assert nid == 2


def test_resilient_to_missing_caption_or_analysis() -> None:
    resolve = _f()
    mp = {2: ["#a"], 3: ["#b"]}
    assert resolve(None, None, mp, 3) == (3, {})
    assert resolve({}, "", mp, 2) == (2, {})


# Audit Pass-2 fix #5 — Python resolver no longer reads Gemini
# ``topics``; it must match the SQL backfill which uses caption +
# hook_phrase only. A topic-only signal must NOT trigger reassignment.


def test_topics_alone_no_longer_reassign() -> None:
    """Sprint 8 SQL backfill matches caption + hook only. Sprint 9's
    resolver previously also matched ``topics[]`` from Gemini analysis,
    creating drift between historical (untouched) and incoming rows.
    Audit Pass-2 fix #5 dropped topics from the haystack."""
    resolve = _f()
    mp = {
        2: ["#skincare", "#skincareroutine", "#chamsocda"],
        3: ["#outfit", "#thoitrang"],
    }
    analysis = {
        "analysis": {
            "topics": ["#outfit", "#thoitrang", "#streetstyle"],
            "hook_analysis": {"hook_phrase": ""},
        },
    }
    nid, _hits = resolve(analysis, "caption không có hashtag", mp, 2)
    assert nid == 2  # topics ignored — no reassignment
