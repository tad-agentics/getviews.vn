"""HI-11 — optional ``NICHE_RESOLVER_MODE=route`` vs default shadow."""

from __future__ import annotations

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline.corpus_ingest import _route_niche_and_class_override
from getviews_pipeline.junction_content_class import (
    content_class_id_for_creator_niche_format,
    primary_content_class_id_by_niche_and_format,
    primary_creator_niche_id_for_content_class,
)


def test_junction_lookup_beauty_tutorial_lowest_cc_id() -> None:
    """Beauty (creator_niche id=1) has two ``tutorial`` rows — deterministic min id."""
    cc_id = content_class_id_for_creator_niche_format(1, "tutorial")
    assert cc_id == 1


def test_junction_lookup_carousel_tutorial() -> None:
    assert content_class_id_for_creator_niche_format(1, "tutorial_carousel") == 75


def test_primary_creator_niche_for_beauty_class() -> None:
    assert primary_creator_niche_id_for_content_class(1) == 1


def test_primary_map_covers_hi16_grid() -> None:
    pmap = primary_content_class_id_by_niche_and_format()
    retired = {5, 13}  # comedy, pets_home — junction removed in 20260728
    for cn in range(1, 17):
        if cn in retired:
            continue
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
    nid, cc = _route_niche_and_class_override(
        analysis, 9, video_id="v", loop_content_class_id=1
    )
    assert nid == 9
    assert cc is None


def test_route_mode_in_niche_class_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route maps format_axis within loop niche — legacy niche unchanged."""
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
    nid, cc = _route_niche_and_class_override(
        analysis,
        9,
        video_id="v",
        loop_content_class_id=1,
        loop_legacy_niche_id=2,
    )
    assert nid == 9
    assert cc == 1


def test_route_mode_cross_niche_gemini_uses_loop_not_inferred_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini beauty + loop gym — legacy niche unchanged; class from gym junction."""
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "route")
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
    nid, cc = _route_niche_and_class_override(
        analysis,
        8,
        video_id="v-gym",
        loop_content_class_id=56,
        loop_legacy_niche_id=8,
    )
    assert nid == 8
    assert cc == 56


def test_route_mode_format_missing_in_loop_niche(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gemini format not seeded for loop niche → no override."""
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "route")
    analysis = {
        "content_type": "video",
        "analysis": {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "live_commerce",
                "confidence": 0.95,
            },
        },
    }
    nid, cc = _route_niche_and_class_override(
        analysis,
        8,
        video_id="v-gym-fmt",
        loop_content_class_id=56,
        loop_legacy_niche_id=8,
    )
    assert nid == 8
    assert cc is None


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
    nid, cc = _route_niche_and_class_override(
        analysis,
        9,
        video_id="v-carousel",
        loop_content_class_id=1,
        loop_legacy_niche_id=2,
    )
    assert nid == 9
    assert cc == 75


def test_route_mode_td6_rejects_non_junction_content_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wave 1b — hard TD-6 gate rejects override when cc_id ∉ junction for niche."""
    from getviews_pipeline.corpus_ingest import (
        get_hi11_junction_reject_count,
        reset_hi11_junction_reject_count,
    )

    reset_hi11_junction_reject_count()
    monkeypatch.setattr(gv_config, "NICHE_RESOLVER_MODE", "route")

    def _fake_cc(_cn: int, _fmt: str) -> int:
        return 99999

    def _fake_has(_cn: int, _cc: int) -> bool:
        return False

    monkeypatch.setattr(
        "getviews_pipeline.junction_content_class.content_class_id_for_creator_niche_format",
        _fake_cc,
    )
    monkeypatch.setattr(
        "getviews_pipeline.junction_content_class.creator_niche_has_content_class",
        _fake_has,
    )

    analysis = {
        "content_type": "video",
        "analysis": {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "review_unboxing",
                "confidence": 0.95,
            },
        },
    }
    nid, cc = _route_niche_and_class_override(
        analysis,
        9,
        video_id="v-td6",
        loop_content_class_id=1,
        loop_legacy_niche_id=2,
    )
    assert nid == 9
    assert cc is None
    assert get_hi11_junction_reject_count() >= 1
