"""HI-11 — shadow niche resolution fields on corpus rows (observability only)."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import _niche_resolution_shadow_fields


def test_shadow_gemini_path_high_confidence() -> None:
    analysis = {
        "niche_classification": {
            "creator_niche_slug": "wellness",
            "confidence": 0.85,
        },
    }
    row = _niche_resolution_shadow_fields(analysis, resolver_niche_id=2, video_id="v1")
    assert row["niche_resolution_source"] == "gemini_two_axis"
    assert row["niche_resolution_confidence"] == 0.85
    assert row["inferred_creator_niche_id"] == 10


def test_shadow_hashtag_path_low_confidence() -> None:
    analysis = {
        "niche_classification": {
            "creator_niche_slug": "wellness",
            "confidence": 0.4,
        },
    }
    row = _niche_resolution_shadow_fields(analysis, resolver_niche_id=2)
    assert row["niche_resolution_source"] == "hashtag"
    assert row["inferred_creator_niche_id"] is None


def test_shadow_missing_classification() -> None:
    row = _niche_resolution_shadow_fields({}, resolver_niche_id=3)
    assert row["niche_resolution_source"] == "hashtag"
    assert row["niche_resolution_confidence"] is None


def test_shadow_unknown_slug() -> None:
    analysis = {"niche_classification": {"creator_niche_slug": "not_a_real_slug", "confidence": 0.99}}
    row = _niche_resolution_shadow_fields(analysis, resolver_niche_id=3)
    assert row["niche_resolution_source"] == "hashtag"
