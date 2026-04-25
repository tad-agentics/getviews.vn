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
#   2026-05-13 Wave 5+ correct-only expansion    — 48/48 = 1.0000
#   2026-05-13 Wave 5+ diagnostic additions      — 49/54 = 0.9074
# Floor at 0.88 tolerates one additional miss (48/54 = 0.889). The
# 2026-05-13 diagnostic batch DELIBERATELY seeded 5 rows where the
# classifier currently fails — each row's ``notes`` documents the
# specific gap + a fix-path hint. Those rows are NOT false-positive
# eval noise; they're the fix list for a future classifier tweak.
# When one gets fixed, raise this floor by 0.018 (1/54) and update
# the baseline line above. Don't "fix" by removing the diagnostic
# row — that erases institutional memory of the gap.
MIN_ACCURACY = 0.88

# Don't regress below this for the 5 highest-traffic buckets. These
# dominate niche_intelligence.format_distribution — getting them
# wrong degrades downstream reports the most.
CORE_CLASSES = {"mukbang", "recipe", "tutorial", "review", "grwm"}
# 2026-05-13 Wave 5+ diagnostic batch seeded 2 known tutorial misses
# (advice-style + educational-skit). Tutorial recall dropped to 0.6
# (3/5). Floor at 0.5 catches a genuine regression (2/5 = 0.4 would
# fail) without needing the diagnostic rows to be fixed first. When
# classifier gets a fix that recovers those 2 rows, bump back to 0.8.
MIN_CORE_RECALL = 0.5


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
