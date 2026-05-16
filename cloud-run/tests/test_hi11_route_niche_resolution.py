"""HI-11 — optional ``NICHE_RESOLVER_MODE=route`` vs default shadow."""

from __future__ import annotations

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline.corpus_ingest import _route_niche_and_class_override
from getviews_pipeline.junction_content_class import (
    content_class_id_for_creator_niche_format,
    primary_content_class_id_by_niche_and_format,
)


def test_junction_lookup_beauty_tutorial_lowest_cc_id() -> None:
    """Beauty (creator_niche id=1) has two ``tutorial`` rows — deterministic min id."""
    cc_id = content_class_id_for_creator_niche_format(1, "tutorial")
    assert cc_id == 1


def test_junction_lookup_carousel_tutorial() -> None:
    assert content_class_id_for_creator_niche_format(1, "tutorial_carousel") == 75


def test_primary_map_covers_hi16_grid() -> None:
    pmap = primary_content_class_id_by_niche_and_format()
    for cn in range(1, 17):
        for fmt in (
            "tutorial_carousel",
            "listicle_carousel",
            "story_carousel",
            "comparison_carousel",
            "gallery_carousel",
        ):
            assert pmap[(cn, fmt)] == {  # maps to HI-16 ids 75–79
                "tutorial_carousel": 75,
                "listicle_carousel": 76,
                "story_carousel": 77,
                "comparison_carousel": 78,
                "gallery_carousel": 79,
            }[fmt]


def test_shadow_mode_returns_hashtag_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "shadow")
    analysis = {
        "content_type": "video",
        "analysis": {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "tutorial",
                "confidence": 0.95,
            },
        },
    }
    nid, cc = _route_niche_and_class_override(analysis, 9, video_id="v")
    assert nid == 9
    assert cc is None


def test_route_mode_gemini_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "route")
    analysis = {
        "content_type": "video",
        "analysis": {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "tutorial",
                "confidence": 0.95,
            },
            "hook_analysis": {},
            "scenes": [],
        },
    }
    nid, cc = _route_niche_and_class_override(analysis, 9, video_id="v")
    assert nid == 2  # legacy Beauty (Skincare)
    assert cc == 1


def test_route_mode_carousel_prefers_carousel_format_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HI-11: carousel path reads ``carousel_format_axis`` (not video ``format_axis``)."""
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "route")
    analysis = {
        "content_type": "carousel",
        "analysis": {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "tutorial",
                "carousel_format_axis": "tutorial_carousel",
                "confidence": 0.95,
            },
            "hook_analysis": {},
            "scenes": [],
        },
    }
    nid, cc = _route_niche_and_class_override(analysis, 9, video_id="v-carousel")
    assert nid == 2
    assert cc == 75