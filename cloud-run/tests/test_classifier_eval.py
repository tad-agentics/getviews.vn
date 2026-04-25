"""CI-integrated eval for ``classify_format``.

Runs ``evaluate()`` against the curated golden set and fails if
accuracy drops below the pinned floor. This is the regression-safety
layer for every PR that touches the classifier — if you reorder
priority, add a regex, or rename a taxonomy value and the golden set
disagrees, CI will tell you before the change lands in main.

Floor policy:
  - The floor is set BELOW the current baseline, not AT it. That gives
    room to accept a single-row regression without blocking an
    otherwise-good change — as long as the fix lands soon.
  - Raising the floor after a classifier improvement is fine. Lowering
    it to mask a regression is NOT; the PR should fix the regression
    or expand the golden set instead.
"""

from __future__ import annotations

from getviews_pipeline.eval_classifier import evaluate, load_golden

# Baseline history:
#   2026-05-09 initial harness                  — 24/27 = 0.8889
#   2026-05-09 + has_speech gate, VN additions  — 27/27 = 1.0000
#   2026-05-13 Wave 5+ expansion 27 → 48 items  — 48/48 = 1.0000
# Floor at 0.97 tolerates one miss on the 48-item set (47/48 = 0.979).
# The 2026-05-13 expansion kept accuracy at 1.0 by only adding items
# the classifier already handles correctly — coverage grew without
# false positives or false negatives to exploit. A follow-up PR
# lands a small set of "diagnostic" misses that DO expose real gaps;
# when that lands the floor drops to match the new measured value
# with a single-miss buffer.
MIN_ACCURACY = 0.97

# Don't regress below this for the 5 highest-traffic buckets. These
# dominate niche_intelligence.format_distribution — getting them
# wrong degrades downstream reports the most.
CORE_CLASSES = {"mukbang", "recipe", "tutorial", "review", "grwm"}
MIN_CORE_RECALL = 0.8


def test_golden_set_loads_and_is_nonempty() -> None:
    items = load_golden()
    # Post-2026-05-13 floor is 40 (Wave 5+ expansion grew the set from
    # 27 → 48). Shrinking below 40 needs explicit review.
    assert len(items) >= 40, (
        f"Golden set shrank to {len(items)} items — re-growing it is fine but "
        "inspection required before loosening."
    )
    # Each item is structurally valid.
    for item in items:
        assert "gold_label" in item
        assert "niche_id" in item
        assert "analysis_json" in item


def test_classifier_accuracy_meets_floor() -> None:
    scorecard = evaluate()
    assert scorecard.accuracy >= MIN_ACCURACY, (
        f"classify_format accuracy {scorecard.accuracy:.4f} below floor "
        f"{MIN_ACCURACY}. Misses:\n"
        + "\n".join(
            f"  {m['video_id']}: gold={m['gold']} pred={m['pred']}"
            for m in scorecard.misses
        )
    )


def test_core_class_recall_is_strong() -> None:
    """High-traffic buckets must stay above MIN_CORE_RECALL. A regression
    on mukbang/recipe/tutorial/review/grwm is disproportionately
    expensive because format_distribution feeds Pattern + Ideas reports."""
    scorecard = evaluate()
    bad = {
        cls: round(scorecard.per_class_recall.get(cls, 0.0), 4)
        for cls in CORE_CLASSES
        if scorecard.per_class_recall.get(cls, 0.0) < MIN_CORE_RECALL
    }
    assert not bad, (
        f"Core class recall regressed below {MIN_CORE_RECALL}: {bad}. "
        "Expand the golden set or fix the classifier."
    )


def test_scorecard_structure_is_well_formed() -> None:
    scorecard = evaluate()
    d = scorecard.as_dict()
    assert d["total"] > 0
    assert 0.0 <= d["accuracy"] <= 1.0
    # Confusion matrix rows sum to per-gold-class total.
    from collections import Counter
    gold_counts: Counter[str] = Counter(i["gold_label"] for i in load_golden())
    for gold, preds in d["confusion"].items():
        assert sum(preds.values()) == gold_counts[gold]
