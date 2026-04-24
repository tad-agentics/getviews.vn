"""CI-safe structural tests for the hook_type eval harness.

Unlike ``test_classifier_eval.py`` (which runs ``classify_format``
locally and gates on accuracy), the hook_type harness requires DB
access — Gemini emits hook_type directly at extraction time, so there
is no local classifier to replay in CI.

What this file covers:
  1. Golden set loads from disk with a sensible minimum size.
  2. Every gold label is a member of the canonical hook_type taxonomy.
  3. Every required per-item field is present and well-formed.
  4. Live accuracy floor (MIN_ACCURACY = 0.85) — skipped unless
     SUPABASE_SERVICE_ROLE_KEY is present (dev + CI skip; prod runs).

The accuracy-floor test is the "production quality gate" referenced in
the plan's Wave 1 exit criteria. When it runs (post-deploy with
credentials), it fails the build if Gemini's hook_type accuracy
regresses below the floor. When it skips (local dev, CI-without-prod-
creds), the other three tests still catch golden-set structural
regressions.
"""

from __future__ import annotations

import os

import pytest

from getviews_pipeline.eval_classifier import (
    evaluate_hook_type,
    load_hook_type_golden,
)

# Current baseline (2026-05-10 live run): 28/31 = 0.903.
# Floor tolerates ~1 additional regression before failing; any regression
# beyond that should either be fixed or force a golden-set re-label.
MIN_ACCURACY = 0.85

# 13 labels observed in live corpus (ignoring unseen ones like warning,
# price_shock, reaction, comparison, expose, pov — listed in the
# normalizer alias map but Gemini has never emitted them in production).
_VALID_LABELS = frozenset({
    "question", "bold_claim", "shock_stat", "story_open", "controversy",
    "challenge", "how_to", "social_proof", "curiosity_gap", "pain_point",
    "trend_hijack", "none", "other",
})

_REQUIRED_FIELDS = {"video_id", "niche_id", "gold_label", "hook_phrase", "transcript_snippet"}


def test_golden_set_loads_and_has_reasonable_size() -> None:
    items = load_hook_type_golden()
    assert len(items) >= 25, (
        f"Golden set shrank to {len(items)} items — re-growing it is fine but "
        "inspection required before loosening."
    )


def test_every_gold_label_is_in_taxonomy() -> None:
    """Catch typos + label-drift from future edits."""
    items = load_hook_type_golden()
    bad = {i["video_id"]: i["gold_label"] for i in items if i["gold_label"] not in _VALID_LABELS}
    assert not bad, (
        f"Gold labels outside taxonomy: {bad}. Add to _VALID_LABELS or fix the item."
    )


def test_every_item_has_required_fields() -> None:
    items = load_hook_type_golden()
    bad: list[str] = []
    for item in items:
        missing = _REQUIRED_FIELDS - set(item.keys())
        if missing:
            bad.append(f"{item.get('video_id')}: missing {sorted(missing)}")
    assert not bad, "Items with missing required fields:\n  " + "\n  ".join(bad)


def test_every_item_has_non_empty_notes() -> None:
    """Every gold label should carry a reviewer's rationale in the
    notes field so ambiguous items can be re-checked later without
    re-deriving the logic."""
    items = load_hook_type_golden()
    missing = [i["video_id"] for i in items if not i.get("notes")]
    assert not missing, (
        f"{len(missing)} items missing rationale notes: {missing[:5]}..."
    )


@pytest.mark.skipif(
    not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason=(
        "Live accuracy eval requires SUPABASE_SERVICE_ROLE_KEY — skipped "
        "in local dev + CI without prod creds."
    ),
)
def test_live_hook_type_accuracy_meets_floor() -> None:
    """Production gate — runs when SUPABASE creds are present.

    Baseline 2026-05-10: 28/31 = 0.903. Floor 0.85 tolerates one
    additional miss before failing.
    """
    scorecard = evaluate_hook_type()
    assert scorecard.accuracy >= MIN_ACCURACY, (
        f"hook_type live accuracy {scorecard.accuracy:.4f} below floor "
        f"{MIN_ACCURACY}. Misses:\n"
        + "\n".join(
            f"  {m['video_id']}: gold={m['gold']} pred={m['pred']}"
            for m in scorecard.misses if m.get("pred") is not None
        )
    )
