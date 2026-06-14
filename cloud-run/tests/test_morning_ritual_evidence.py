"""L2.2 Sprint 4 — per-script evidence picker tests.

Pins the contract for ``_pick_evidence_for_script`` (the helper that
filters the ritual's grounding pool down to up-to-12 video_ids whose
hook_type matches the chosen script). The FE hydrates these into a
"Xem 12 video tương tự" thumbnail strip on the StudioHero row.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.morning_ritual import (
    EVIDENCE_PER_SCRIPT,
    _evidence_pool_slice,
    _pick_evidence_for_script,
)


def _v(video_id: str, hook_type: str) -> dict[str, Any]:
    """Pool entry stub — only the fields the picker reads."""
    return {"video_id": video_id, "hook_type": hook_type}


# ── Hook-matched picks ───────────────────────────────────────────────────


def test_picks_hook_matched_videos_when_enough_exist() -> None:
    """When ≥4 videos match the script's hook_type, return only those.

    Fallback rows must NOT leak in — the strip's framing is "this hook
    is winning here", so mixing in unrelated hooks would mislead.
    """
    pool = [_v(f"m{i}", "comparison") for i in range(5)] + [
        _v("o1", "pov"),
        _v("o2", "story_open"),
    ]
    out = _pick_evidence_for_script(pool, "comparison")
    assert out == ["m0", "m1", "m2", "m3", "m4"]


def test_caps_at_evidence_per_script_limit() -> None:
    pool = [_v(f"m{i}", "warning") for i in range(EVIDENCE_PER_SCRIPT + 5)]
    out = _pick_evidence_for_script(pool, "warning")
    assert len(out) == EVIDENCE_PER_SCRIPT
    # Pool order (views-DESC) is preserved.
    assert out == [f"m{i}" for i in range(EVIDENCE_PER_SCRIPT)]


def test_respects_explicit_smaller_limit() -> None:
    pool = [_v(f"m{i}", "expose") for i in range(8)]
    out = _pick_evidence_for_script(pool, "expose", limit=3)
    assert out == ["m0", "m1", "m2"]


def test_hook_match_is_case_insensitive_and_trimmed() -> None:
    """video_corpus.hook_type historically had inconsistent casing /
    whitespace; the picker normalises both sides so we don't lose
    legitimate matches."""
    pool = [
        _v("a1", "  Comparison "),
        _v("a2", "COMPARISON"),
        _v("a3", "comparison"),
        _v("a4", "comparison"),
    ]
    out = _pick_evidence_for_script(pool, "comparison")
    assert out == ["a1", "a2", "a3", "a4"]


# ── Fallback (sparse hook match) ────────────────────────────────────────


def test_falls_back_to_top_of_pool_when_below_min_match() -> None:
    """With only 1-3 hook-matched videos we don't have a credible
    evidence strip — top up with the highest-views videos from the rest
    of the pool. Matched go first (they're still the best evidence for
    *this* hook); fallback fills the remainder in pool order."""
    pool = [
        _v("m1", "warning"),         # only one match
        _v("o1", "pov"),
        _v("o2", "story_open"),
        _v("o3", "comparison"),
        _v("o4", "expose"),
    ]
    out = _pick_evidence_for_script(pool, "warning")
    # Matched first, then fallback in pool order, capped at limit.
    assert out == ["m1", "o1", "o2", "o3", "o4"]


def test_returns_top_of_pool_when_zero_hook_matches() -> None:
    pool = [_v(f"o{i}", "pov") for i in range(6)]
    out = _pick_evidence_for_script(pool, "warning", limit=4)
    assert out == ["o0", "o1", "o2", "o3"]


# ── Edge cases ──────────────────────────────────────────────────────────


def test_empty_pool_returns_empty() -> None:
    assert _pick_evidence_for_script([], "comparison") == []


def test_skips_entries_missing_video_id() -> None:
    pool = [
        {"video_id": None, "hook_type": "warning"},
        {"hook_type": "warning"},                  # missing key
        _v("", "warning"),                          # empty string
        _v("good1", "warning"),
        _v("good2", "warning"),
        _v("good3", "warning"),
        _v("good4", "warning"),
    ]
    out = _pick_evidence_for_script(pool, "warning")
    assert out == ["good1", "good2", "good3", "good4"]


def test_handles_missing_hook_type_on_pool_entries() -> None:
    """Some legacy corpus rows have NULL hook_type; they should never
    match the script's hook_type but can still serve as fallback."""
    pool = [
        {"video_id": "n1", "hook_type": None},
        {"video_id": "n2"},                        # missing key
        _v("m1", "comparison"),
    ]
    # Only 1 match → fallback kicks in, hook-less rows fill remainder.
    out = _pick_evidence_for_script(pool, "comparison")
    assert out == ["m1", "n1", "n2"]


def test_empty_target_hook_returns_top_of_pool() -> None:
    """Defensive: a missing/blank ``hook_type_en`` shouldn't crash;
    returning the top of the pool is a safe (if rare) fallback."""
    pool = [_v(f"o{i}", "pov") for i in range(3)]
    out = _pick_evidence_for_script(pool, "")
    assert out == ["o0", "o1", "o2"]


def test_exclude_ids_skips_already_assigned_videos() -> None:
    pool = [_v(f"o{i}", "pov") for i in range(6)]
    out = _pick_evidence_for_script(pool, "pov", limit=3, exclude_ids={"o0", "o1"})
    assert out == ["o2", "o3", "o4"]


def test_evidence_pool_slice_partitions_without_overlap() -> None:
    """20-video grounding pool → 7 + 7 + 6 across three ritual rows."""
    pool = [_v(f"v{i}", "pov") for i in range(20)]
    slices = [_evidence_pool_slice(pool, i, 3) for i in range(3)]
    assert [len(s) for s in slices] == [7, 7, 6]
    all_ids = [v["video_id"] for s in slices for v in s]
    assert len(all_ids) == len(set(all_ids)) == 20


def test_three_rows_get_distinct_strips_from_shared_pool() -> None:
    """Simulates sparse hook match on a 20-video pool — rows must not
    converge on the same top-12 fallback thumbs."""
    pool = [_v(f"v{i}", "pov") for i in range(20)]
    strips: list[list[str]] = []
    for i in range(3):
        row_pool = _evidence_pool_slice(pool, i, 3)
        strips.append(
            _pick_evidence_for_script(
                row_pool,
                "warning",  # zero hook matches → slice fallback only
                limit=min(EVIDENCE_PER_SCRIPT, len(row_pool)),
            )
        )
    assert [len(s) for s in strips] == [7, 7, 6]
    flat = [vid for strip in strips for vid in strip]
    assert len(flat) == len(set(flat)) == 20
