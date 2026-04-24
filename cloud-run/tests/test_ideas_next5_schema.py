"""Wave 2 PR #2 — `IdeaBlockPayload` schema + `compute_ideas_blocks`
populates the 3 new fields (`rank`, `opening_line`, `lifecycle_stage`)
deterministically. These tests pin what the frontend "5 video tiếp
theo" layout needs to render, before the Gemini prompt upgrade
(Wave 2 PR #3) replaces the templates with video-specific strings.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.report_ideas_compute import (
    _TREND_TO_LIFECYCLE,
    _opening_line_template,
    compute_ideas_blocks,
)
from getviews_pipeline.report_types import IdeaBlockPayload

# ── Schema back-compat ───────────────────────────────────────────────

def test_new_fields_default_to_legacy_compat_values() -> None:
    """Old fixtures constructed without the new fields still validate."""
    block = IdeaBlockPayload(
        id="01",
        title="T",
        tag="t",
        angle="a",
        why_works="w",
        evidence_video_ids=[],
        hook="h",
        slides=[],
        metric={"label": "", "value": "", "range": ""},
        prerequisites=[],
        confidence={"sample_size": 0},
        style="s",
    )
    assert block.rank == 0
    assert block.opening_line == ""
    assert block.lifecycle_stage is None


def test_new_fields_accept_explicit_values() -> None:
    block = IdeaBlockPayload(
        id="01", title="T", tag="t", angle="a", why_works="w",
        evidence_video_ids=[], hook="h", slides=[],
        metric={"label": "", "value": "", "range": ""},
        prerequisites=[], confidence={"sample_size": 0}, style="s",
        rank=3, opening_line="Bạn đã bao giờ thử...",
        lifecycle_stage="peak",
    )
    assert block.rank == 3
    assert block.opening_line.startswith("Bạn đã bao giờ")
    assert block.lifecycle_stage == "peak"


def test_lifecycle_stage_rejects_off_taxonomy_values() -> None:
    """Pydantic Literal catches typos — surface at validation boundary."""
    import pytest
    with pytest.raises(Exception):  # ValidationError but import-safe for plain Exception
        IdeaBlockPayload(
            id="01", title="T", tag="t", angle="a", why_works="w",
            evidence_video_ids=[], hook="h", slides=[],
            metric={"label": "", "value": "", "range": ""},
            prerequisites=[], confidence={"sample_size": 0}, style="s",
            lifecycle_stage="emerging",  # not in ("early","peak","decline")
        )


# ── compute_ideas_blocks populates new fields ────────────────────────

def _hook_row(hook_type: str, trend: str = "stable") -> dict[str, Any]:
    return {
        "hook_type": hook_type,
        "avg_views": 10_000,
        "avg_engagement_rate": 0.05,
        "avg_completion_rate": 0.55,
        "sample_size": 8,
        "trend_direction": trend,
    }


def test_rank_is_1_indexed_position() -> None:
    rows = [_hook_row(h) for h in ("question", "bold_claim", "how_to")]
    blocks = compute_ideas_blocks(rows, corpus_rows=[], baseline_views=1.0)
    assert [b.rank for b in blocks] == [1, 2, 3]


def test_lifecycle_stage_mapped_from_trend_direction() -> None:
    rows = [
        _hook_row("question", trend="rising"),
        _hook_row("bold_claim", trend="stable"),
        _hook_row("how_to", trend="declining"),
    ]
    blocks = compute_ideas_blocks(rows, corpus_rows=[], baseline_views=1.0)
    assert blocks[0].lifecycle_stage == "early"
    assert blocks[1].lifecycle_stage == "peak"
    assert blocks[2].lifecycle_stage == "decline"


def test_lifecycle_stage_unknown_trend_stays_none() -> None:
    """An unexpected trend value shouldn't force a (possibly wrong)
    lifecycle — let the UI render without the pill."""
    rows = [_hook_row("question", trend="")]
    blocks = compute_ideas_blocks(rows, corpus_rows=[], baseline_views=1.0)
    assert blocks[0].lifecycle_stage is None


def test_opening_line_populated_per_hook_type() -> None:
    """Every hook_type in _opening_line_template has a distinct opener —
    no two blocks with different hook_types share the exact same line."""
    rows = [_hook_row(ht) for ht in (
        "question", "bold_claim", "story_open", "pain_point", "how_to",
    )]
    blocks = compute_ideas_blocks(rows, corpus_rows=[], baseline_views=1.0)
    openers = {b.hook_type: b.opening_line for b in (
        type("B", (), {"hook_type": r["hook_type"], "opening_line": bk.opening_line})
        for r, bk in zip(rows, blocks)
    )}
    assert len(set(openers.values())) == len(rows), (
        f"Openers not distinct across hook types: {openers}"
    )


def test_opening_line_nonempty_and_bounded() -> None:
    """Structure test: every block gets a non-empty opening line ≤120 chars."""
    rows = [_hook_row(h) for h in ("question", "challenge", "trend_hijack")]
    blocks = compute_ideas_blocks(rows, corpus_rows=[], baseline_views=1.0)
    for b in blocks:
        assert b.opening_line
        assert len(b.opening_line) <= 120


def test_template_direct_for_unknown_hook_type() -> None:
    """An unknown hook_type falls through to a generic `Hôm nay: {label}.`
    template rather than emitting an empty string."""
    line = _opening_line_template("Xyz", "completely_new_hook_type")
    assert line.startswith("Hôm nay:")


def test_trend_lifecycle_mapping_coverage() -> None:
    """Pin the mapping so any future rename (e.g. 'rising'→'ascending')
    in hook_effectiveness_compute.py surfaces here first."""
    assert _TREND_TO_LIFECYCLE == {
        "rising": "early",
        "stable": "peak",
        "declining": "decline",
    }
