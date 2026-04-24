"""Wave 2.5 Phase B PR #5 — shot reference matcher tests.

Pins:

* niche_id is a hard filter (wrong-niche rows never return even if
  every other dimension matches)
* hook_type adds +40 when both sides are non-null AND equal
* Each enrichment dimension is additive; NULL on either side neither
  scores nor penalizes
* scene_type fallback fires only when framing is NULL on both sides
* Tiebreaker: frame_url > thumbnail_url > video_id
* Match signals → VN label ("Cùng ngách, hook, khung hình")
* exclude_video_ids de-dupes across shots within one script
* Min-score threshold filters below-noise matches
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.shot_reference_matcher import (
    ShotReference,
    _match_label_vn,
    _score_shot,
    _tiebreaker_key,
    pick_shot_references,
)


def _shot(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "video_id": "v1",
        "scene_index": 0,
        "start_s": 0.5, "end_s": 3.0,
        "scene_type": "face_to_camera",
        "framing": "close_up", "pace": "slow",
        "overlay_style": "bold_center", "subject": "face", "motion": "static",
        "hook_type": "question",
        "creator_handle": "@cr",
        "thumbnail_url": "https://cdn/thumb.jpg",
        "tiktok_url": "https://tiktok.com/@cr/video/v1",
        "frame_url": "https://cdn/v1/0.jpg",
        "description": "Cận mặt creator.",
    }
    base.update(overrides)
    return base


def _mock_client(rows: list[dict[str, Any]]) -> MagicMock:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=rows)
    client = MagicMock()
    client.table.return_value = chain
    return client


# ── _score_shot — additive, NULL-tolerant ────────────────────────────

def test_score_zero_when_descriptor_fully_mismatches() -> None:
    shot = _shot(
        framing="wide", pace="fast", overlay_style="none",
        subject="product", motion="handheld", hook_type="bold_claim",
    )
    desc = {
        "framing": "close_up", "pace": "slow",
        "overlay_style": "bold_center", "subject": "face", "motion": "static",
    }
    score, matched = _score_shot(shot, desc, hook_type="question")
    assert score == 0
    assert matched == []


def test_score_full_match_max_points() -> None:
    """hook (40) + framing (15) + pace (15) + overlay (10) + subject (10)
    + motion (5) = 95."""
    shot = _shot()
    desc = {
        "framing": "close_up", "pace": "slow", "overlay_style": "bold_center",
        "subject": "face", "motion": "static",
    }
    score, matched = _score_shot(shot, desc, hook_type="question")
    assert score == 95
    assert set(matched) == {
        "hook", "framing", "pace", "overlay", "subject", "motion",
    }


def test_score_null_descriptor_field_neither_scores_nor_penalizes() -> None:
    shot = _shot()
    desc = {"framing": "close_up"}  # only one dim specified
    score, matched = _score_shot(shot, desc, hook_type="question")
    assert score == 40 + 15  # hook + framing
    assert matched == ["hook", "framing"]


def test_score_null_shot_field_does_not_match() -> None:
    """An un-enriched shot (framing=NULL) shouldn't match a descriptor
    with framing=close_up on that dimension."""
    shot = _shot(framing=None, pace=None)
    desc = {"framing": "close_up", "pace": "slow"}
    score, matched = _score_shot(shot, desc, hook_type=None)
    assert score == 0
    assert matched == []


def test_score_hook_type_requires_both_non_null_and_equal() -> None:
    shot = _shot(hook_type="question")
    # descriptor hook_type matches
    s1, _ = _score_shot(shot, {}, hook_type="question")
    assert s1 == 40
    # descriptor hook_type mismatches
    s2, _ = _score_shot(shot, {}, hook_type="bold_claim")
    assert s2 == 0
    # shot hook_type NULL — no score even if descriptor has it
    shot_no_hook = _shot(hook_type=None)
    s3, _ = _score_shot(shot_no_hook, {}, hook_type="question")
    assert s3 == 0


# ── scene_type fallback ──────────────────────────────────────────────

def test_scene_type_fallback_fires_when_framing_null_on_both_sides() -> None:
    """Legacy (pre-PR #2) shots have no framing; descriptor may also
    be legacy. scene_type should still earn +10."""
    shot = _shot(framing=None, scene_type="face_to_camera")
    desc = {"framing": None, "scene_type": "face_to_camera"}
    score, matched = _score_shot(shot, desc, hook_type=None)
    assert score == 10
    assert matched == ["scene_type"]


def test_scene_type_fallback_does_not_fire_when_descriptor_has_framing() -> None:
    """If the new descriptor knows framing, scene_type is redundant —
    don't double-score the same semantic dimension."""
    shot = _shot(framing=None, scene_type="face_to_camera")
    desc = {"framing": "close_up", "scene_type": "face_to_camera"}
    score, matched = _score_shot(shot, desc, hook_type=None)
    # No framing on shot → no framing score; no fallback because
    # descriptor had framing set.
    assert score == 0
    assert matched == []


def test_scene_type_fallback_does_not_fire_when_shot_has_framing() -> None:
    shot = _shot(framing="wide", scene_type="face_to_camera")
    desc = {"framing": None, "scene_type": "face_to_camera"}
    score, matched = _score_shot(shot, desc, hook_type=None)
    assert score == 0


# ── Tiebreaker ordering ──────────────────────────────────────────────

def test_tiebreaker_prefers_frame_url_then_thumbnail() -> None:
    a = ShotReference(
        video_id="a", scene_index=0, start_s=0, end_s=1,
        frame_url=None, thumbnail_url="t", tiktok_url=None,
        creator_handle=None, description=None, score=50,
    )
    b = ShotReference(
        video_id="b", scene_index=0, start_s=0, end_s=1,
        frame_url="f", thumbnail_url="t", tiktok_url=None,
        creator_handle=None, description=None, score=50,
    )
    c = ShotReference(
        video_id="c", scene_index=0, start_s=0, end_s=1,
        frame_url=None, thumbnail_url=None, tiktok_url=None,
        creator_handle=None, description=None, score=50,
    )
    ordered = sorted([a, b, c], key=_tiebreaker_key)
    assert [r.video_id for r in ordered] == ["b", "a", "c"]


# ── Match label VN ──────────────────────────────────────────────────

def test_match_label_vn_joins_signals() -> None:
    label = _match_label_vn(["niche", "hook", "framing", "pace"])
    assert label == "Cùng ngách, hook, khung hình, nhịp"


def test_match_label_vn_empty_returns_empty() -> None:
    assert _match_label_vn([]) == ""


def test_match_label_vn_unknown_signal_passes_through() -> None:
    """Unknown keys render verbatim — a new dimension shouldn't crash
    the label builder."""
    assert "mystery" in _match_label_vn(["niche", "mystery"])


# ── pick_shot_references — end-to-end against mocked client ─────────

def test_pick_returns_up_to_limit_sorted_by_score_desc() -> None:
    # b = full match (95). c = full minus pace (80). mid = hook+framing only (55).
    # noise = nothing matches (0).
    client = _mock_client([
        _shot(video_id="noise", hook_type="bold_claim", framing="wide",
              pace="fast", overlay_style="none", subject="product",
              motion="handheld"),                            # 0 pts
        _shot(video_id="b"),                                 # 95 pts
        _shot(video_id="c", pace="fast"),                    # 80 pts
        _shot(video_id="mid", pace="fast", overlay_style="none",
              subject="product", motion="handheld"),         # 55 pts
    ])
    refs = pick_shot_references(
        shot_descriptor={
            "framing": "close_up", "pace": "slow",
            "overlay_style": "bold_center", "subject": "face",
            "motion": "static",
        },
        niche_id=7,
        hook_type="question",
        limit=2,
        client=client,
    )
    assert [r.video_id for r in refs] == ["b", "c"]
    assert refs[0].score > refs[1].score
    # niche is always present in match_signals
    assert "niche" in refs[0].match_signals


def test_pick_hard_filters_on_niche_via_eq() -> None:
    """We don't assert that the query returned only niche=7 — we assert
    the client was called with .eq('niche_id', 7) to narrow at the SQL
    level."""
    client = _mock_client([_shot()])
    pick_shot_references(
        shot_descriptor={"framing": "close_up"},
        niche_id=7,
        hook_type="question",
        client=client,
    )
    eq_call = client.table.return_value.eq
    eq_call.assert_any_call("niche_id", 7)


def test_pick_min_score_filters_weak_matches() -> None:
    client = _mock_client([
        _shot(video_id="weak", hook_type=None, framing="wide",
              pace="fast", overlay_style="none", subject="product",
              motion="handheld"),                            # 0 pts
        _shot(video_id="ok", hook_type=None),                # 55 pts (5 dims)
    ])
    refs = pick_shot_references(
        shot_descriptor={
            "framing": "close_up", "pace": "slow",
            "overlay_style": "bold_center", "subject": "face",
            "motion": "static",
        },
        niche_id=7,
        client=client,
        min_score=15,
    )
    assert [r.video_id for r in refs] == ["ok"]


def test_pick_exclude_video_ids_de_duplicates() -> None:
    client = _mock_client([
        _shot(video_id="v_same", scene_index=0),
        _shot(video_id="v_same", scene_index=1),
        _shot(video_id="v_other", scene_index=0),
    ])
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up"},
        niche_id=7,
        hook_type="question",
        exclude_video_ids={"v_same"},
        client=client,
    )
    assert [r.video_id for r in refs] == ["v_other"]


def test_pick_returns_empty_when_db_raises() -> None:
    client = MagicMock()
    client.table.side_effect = RuntimeError("supabase down")
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up"},
        niche_id=7,
        client=client,
    )
    assert refs == []


def test_pick_returns_empty_when_niche_empty() -> None:
    client = _mock_client([])
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up"},
        niche_id=999,
        client=client,
    )
    assert refs == []


def test_pick_returns_empty_when_niche_id_non_int() -> None:
    client = _mock_client([_shot()])
    refs = pick_shot_references(
        shot_descriptor={"framing": "close_up"},
        niche_id="seven",  # type: ignore[arg-type]
        client=client,
    )
    assert refs == []


# ── Match label payload ─────────────────────────────────────────────

def test_match_label_includes_all_matched_dimensions() -> None:
    client = _mock_client([_shot()])  # full match
    refs = pick_shot_references(
        shot_descriptor={
            "framing": "close_up", "pace": "slow",
            "overlay_style": "bold_center", "subject": "face",
            "motion": "static",
        },
        niche_id=7,
        hook_type="question",
        client=client,
    )
    assert len(refs) == 1
    r = refs[0]
    assert r.match_label.startswith("Cùng ngách")
    assert "hook" in r.match_label
    assert "khung hình" in r.match_label
    assert "nhịp" in r.match_label


def test_match_signals_always_starts_with_niche() -> None:
    client = _mock_client([_shot(hook_type=None, framing=None, pace=None,
                                 overlay_style=None, subject=None, motion=None,
                                 scene_type="face_to_camera")])
    refs = pick_shot_references(
        shot_descriptor={
            "scene_type": "face_to_camera",
            # Descriptor also lacks enrichment → scene_type fallback
            # earns the matcher just 10 points. Below default min_score=15.
        },
        niche_id=7,
        client=client,
        min_score=5,
    )
    assert len(refs) == 1
    assert refs[0].match_signals[0] == "niche"


# ── ShotReference serialization ─────────────────────────────────────

def test_to_dict_round_trip() -> None:
    ref = ShotReference(
        video_id="v1", scene_index=0, start_s=0.5, end_s=3.0,
        frame_url="https://cdn/0.jpg", thumbnail_url="https://cdn/t.jpg",
        tiktok_url="https://tiktok.com/…", creator_handle="@cr",
        description="Cận mặt.", score=70,
        match_signals=["niche", "hook"], match_label="Cùng ngách, hook",
    )
    d = ref.to_dict()
    assert d["video_id"] == "v1"
    assert d["score"] == 70
    assert d["match_label"] == "Cùng ngách, hook"
    assert d["match_signals"] == ["niche", "hook"]


# ── Parametrized scoring sanity ─────────────────────────────────────

@pytest.mark.parametrize("field,value,expected_score", [
    ("framing", "close_up", 15),
    ("pace", "slow", 15),
    ("overlay_style", "bold_center", 10),
    ("subject", "face", 10),
    ("motion", "static", 5),
])
def test_per_dimension_weights_are_stable(
    field: str, value: str, expected_score: int,
) -> None:
    shot = _shot(**{field: value, "hook_type": None,
                    "framing": None if field != "framing" else value,
                    "pace": None if field != "pace" else value,
                    "overlay_style": None if field != "overlay_style" else value,
                    "subject": None if field != "subject" else value,
                    "motion": None if field != "motion" else value,
                    "scene_type": None})
    desc = {field: value}
    score, matched = _score_shot(shot, desc, hook_type=None)
    assert score == expected_score
    assert len(matched) == 1
