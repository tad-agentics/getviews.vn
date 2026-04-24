"""Wave 2.5 Phase A PR #2 — Scene schema enrichment.

Pins two behaviors:

1. New enrichment fields (framing / pace / overlay_style / subject /
   motion / description) are Optional — existing ingest rows built
   without them still validate.

2. Enum values reject off-taxonomy inputs at validation boundary —
   a Gemini hallucination like ``pace="very_fast"`` surfaces as a
   ValidationError rather than silently corrupting the corpus.

These tests do NOT invoke Gemini — they exercise the Pydantic contract
directly. Gemini-side accuracy (does the model actually emit consistent
framing labels?) is tracked separately by the scene-enrichment eval
harness in a later commit.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from getviews_pipeline.models import Scene


def _scene_kwargs(**overrides):
    base = {"type": "face_to_camera", "start": 0.0, "end": 2.5}
    base.update(overrides)
    return base


# ── Back-compat — legacy minimal Scene still validates ──────────────

def test_legacy_scene_without_enrichment_validates() -> None:
    """An ingest row from before 2026-05-10 (no enrichment fields)
    must still deserialize into the new Scene model."""
    s = Scene(**_scene_kwargs())
    assert s.type == "face_to_camera"
    assert s.framing is None
    assert s.pace is None
    assert s.overlay_style is None
    assert s.subject is None
    assert s.motion is None
    assert s.description is None


def test_scene_with_all_enrichment_populated() -> None:
    s = Scene(**_scene_kwargs(
        framing="close_up",
        pace="slow",
        overlay_style="bold_center",
        subject="face",
        motion="handheld",
        description="Cận mặt creator nói câu mở, text vàng ở trên.",
    ))
    assert s.framing == "close_up"
    assert s.pace == "slow"
    assert s.overlay_style == "bold_center"
    assert s.subject == "face"
    assert s.motion == "handheld"
    assert s.description.startswith("Cận mặt")


# ── Enum validation — reject off-taxonomy inputs ────────────────────

@pytest.mark.parametrize("field,bad_value", [
    ("framing", "super_close"),
    ("framing", "CLOSE_UP"),          # case-sensitive Literal
    ("pace", "very_fast"),
    ("pace", "crazy"),
    ("overlay_style", "watermark"),   # not in taxonomy
    ("overlay_style", "Bold_Center"),
    ("subject", "person"),             # close-but-wrong
    ("subject", "text_overlay"),
    ("motion", "tracking"),            # not in taxonomy
    ("motion", "STATIC"),
])
def test_enrichment_field_rejects_off_taxonomy(field: str, bad_value: str) -> None:
    with pytest.raises(ValidationError):
        Scene(**_scene_kwargs(**{field: bad_value}))


# ── Partial population — Gemini may only emit 2 of 6 fields ─────────

def test_partial_enrichment_is_acceptable() -> None:
    """Gemini returning framing + pace only (because it couldn't
    classify overlay_style confidently) must still validate. The
    matcher handles null dimensions by skipping them in the scoring."""
    s = Scene(**_scene_kwargs(
        framing="medium",
        pace="fast",
        # overlay_style / subject / motion / description omitted
    ))
    assert s.framing == "medium"
    assert s.pace == "fast"
    assert s.overlay_style is None
    assert s.subject is None


# ── Description is free-form string, not constrained by Literal ─────

def test_description_accepts_any_vn_string() -> None:
    # No length cap on the Pydantic side — caller trims if needed.
    s = Scene(**_scene_kwargs(description="B-roll sản phẩm xoay chậm trên bàn."))
    assert "B-roll" in s.description


def test_description_empty_string_treated_as_none_on_our_side() -> None:
    """Pydantic accepts empty string but downstream writer should
    coerce to None. This test just documents that Pydantic validates
    the empty string — coercion logic belongs in the writer (PR #4)."""
    s = Scene(**_scene_kwargs(description=""))
    assert s.description == ""  # Pydantic allows; writer decides


# ── Taxonomy membership sanity ──────────────────────────────────────

def test_framing_taxonomy_is_what_the_docstring_says() -> None:
    """If someone renames close_up → closeup, this test catches it
    before the matcher queries start returning empty rows."""
    from typing import get_args

    from getviews_pipeline.models import FramingType
    assert set(get_args(FramingType)) == {
        "close_up", "medium", "wide", "extreme_close_up",
    }


def test_pace_taxonomy_is_stable() -> None:
    from typing import get_args

    from getviews_pipeline.models import PaceType
    assert set(get_args(PaceType)) == {
        "static", "slow", "medium", "fast", "cut_heavy",
    }


def test_overlay_style_taxonomy_is_stable() -> None:
    from typing import get_args

    from getviews_pipeline.models import OverlayStyleType
    assert set(get_args(OverlayStyleType)) == {
        "none", "bold_center", "sub_caption", "chyron", "sticker",
    }


def test_subject_taxonomy_is_stable() -> None:
    from typing import get_args

    from getviews_pipeline.models import SubjectType
    assert set(get_args(SubjectType)) == {
        "face", "product", "text", "action", "ambient", "mixed",
    }


def test_motion_taxonomy_is_stable() -> None:
    from typing import get_args

    from getviews_pipeline.models import MotionType
    assert set(get_args(MotionType)) == {
        "static", "handheld", "slow_mo", "time_lapse", "match_cut",
    }
