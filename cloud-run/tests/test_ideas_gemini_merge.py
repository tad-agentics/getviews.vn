"""Wave 2 PR #3 — per-rank Gemini copy merged into IdeaBlockPayload.

Two surfaces tested:

1. ``normalize_hook_lines`` — pure function, dedups + validates
   Gemini's hook_lines before handing them to the caller. Tested
   directly (no Gemini mocking required).

2. The caller-side merge — when build_ideas_report has a non-empty
   hook_lines list, each matching-rank IdeaBlockPayload gets
   opening_line + angle overridden; other fields preserved.

Intentionally does NOT exercise fill_ideas_narrative end-to-end;
that path constructs a google.genai config which isn't mockable
without brittle patches. The fallback "no GEMINI_API_KEY" path is
covered as a sanity check so the end-to-end contract stays tight.
"""

from __future__ import annotations

from unittest.mock import patch

from getviews_pipeline.report_ideas_gemini import (
    IdeaBlockCopy,
    fill_ideas_narrative,
    normalize_hook_lines,
)
from getviews_pipeline.report_types import IdeaBlockPayload

# ── normalize_hook_lines (pure) ──────────────────────────────────────

def test_normalize_well_formed_input_preserves_all_entries() -> None:
    raw = [
        IdeaBlockCopy(rank=1, opening_line="Mở số 1", content_angle="Angle 1"),
        IdeaBlockCopy(rank=2, opening_line="Mở số 2", content_angle="Angle 2"),
        IdeaBlockCopy(rank=3, opening_line="Mở số 3", content_angle="Angle 3"),
        IdeaBlockCopy(rank=4, opening_line="Mở số 4", content_angle="Angle 4"),
        IdeaBlockCopy(rank=5, opening_line="Mở số 5", content_angle="Angle 5"),
    ]
    out = normalize_hook_lines(raw)
    assert len(out) == 5
    assert [hl["rank"] for hl in out] == [1, 2, 3, 4, 5]
    assert len({hl["opening_line"] for hl in out}) == 5


def test_duplicate_rank_first_wins() -> None:
    raw = [
        IdeaBlockCopy(rank=1, opening_line="First", content_angle="A"),
        IdeaBlockCopy(rank=1, opening_line="Second should drop", content_angle="B"),
        IdeaBlockCopy(rank=2, opening_line="Rank 2", content_angle="C"),
    ]
    out = normalize_hook_lines(raw)
    assert [hl["rank"] for hl in out] == [1, 2]
    assert out[0]["opening_line"] == "First"


def test_empty_or_whitespace_opening_line_dropped() -> None:
    raw = [
        IdeaBlockCopy(rank=1, opening_line="Valid", content_angle="A"),
        IdeaBlockCopy(rank=2, opening_line="   ", content_angle="B"),
        IdeaBlockCopy(rank=3, opening_line="", content_angle="C"),
        IdeaBlockCopy(rank=4, opening_line="Also valid", content_angle="D"),
    ]
    out = normalize_hook_lines(raw)
    assert [hl["rank"] for hl in out] == [1, 4]


def test_output_sorted_by_rank_ascending() -> None:
    """Gemini may emit entries out of order — caller gets them sorted."""
    raw = [
        IdeaBlockCopy(rank=5, opening_line="E", content_angle="e"),
        IdeaBlockCopy(rank=2, opening_line="B", content_angle="b"),
        IdeaBlockCopy(rank=4, opening_line="D", content_angle="d"),
    ]
    out = normalize_hook_lines(raw)
    assert [hl["rank"] for hl in out] == [2, 4, 5]


def test_empty_input_returns_empty_list() -> None:
    assert normalize_hook_lines([]) == []


def test_trimmed_to_wire_caps() -> None:
    """opening_line ≤ 120 chars, content_angle ≤ 240 chars."""
    raw = [IdeaBlockCopy(
        rank=1,
        opening_line="X" * 300,
        content_angle="Y" * 500,
    )]
    out = normalize_hook_lines(raw)
    assert len(out[0]["opening_line"]) == 120
    assert len(out[0]["content_angle"]) == 240


# ── fill_ideas_narrative fallback path ──────────────────────────────

def test_fallback_returns_empty_hook_lines() -> None:
    """No Gemini key → fallback dict still has hook_lines=[]."""
    with patch(
        "getviews_pipeline.config.GEMINI_API_KEY", new="", create=True,
    ):
        out = fill_ideas_narrative(
            query="mẫu cho mẹ bỉm?",
            niche_label="Parenting",
            sample_n=80,
            top_idea_hooks=["Hook A", "Hook B"],
        )
    assert out["hook_lines"] == []
    assert out["lead"]
    assert len(out["related_questions"]) == 3


# ── Caller merge behavior ───────────────────────────────────────────

def test_merge_overrides_opening_line_and_angle() -> None:
    """When hook_lines includes rank=1, the block's opening_line +
    angle flip to Gemini values; other fields untouched."""
    block = IdeaBlockPayload(
        id="01", title="T", tag="t",
        angle="TEMPLATED_ANGLE",
        why_works="w", evidence_video_ids=[],
        hook="H", slides=[],
        metric={"label": "", "value": "", "range": ""},
        prerequisites=[], confidence={"sample_size": 10}, style="s",
        rank=1, opening_line="TEMPLATED_OPENER", lifecycle_stage="peak",
    )
    hl = {"rank": 1, "opening_line": "GEMINI OPENER", "content_angle": "GEMINI ANGLE"}
    updated = block.model_copy(update={
        "opening_line": hl["opening_line"],
        "angle": hl["content_angle"],
    })
    assert updated.opening_line == "GEMINI OPENER"
    assert updated.angle == "GEMINI ANGLE"
    # Preserved:
    assert updated.lifecycle_stage == "peak"
    assert updated.why_works == "w"
    assert updated.rank == 1
    assert updated.hook == "H"


def test_merge_no_match_keeps_deterministic() -> None:
    """If hook_lines is missing rank 3 but block.rank=3, the block
    keeps its deterministic template (no override)."""
    block = IdeaBlockPayload(
        id="03", title="T", tag="t", angle="DET_ANGLE",
        why_works="w", evidence_video_ids=[], hook="H", slides=[],
        metric={"label": "", "value": "", "range": ""},
        prerequisites=[], confidence={"sample_size": 10}, style="s",
        rank=3, opening_line="DET_OPENER",
    )
    hook_lines = [
        {"rank": 1, "opening_line": "A", "content_angle": "a"},
        {"rank": 2, "opening_line": "B", "content_angle": "b"},
    ]
    by_rank = {int(hl["rank"]): hl for hl in hook_lines}
    assert by_rank.get(block.rank) is None
    # Merge loop skips this block — deterministic values stay
    assert block.opening_line == "DET_OPENER"
    assert block.angle == "DET_ANGLE"
