"""CI-integrated eval for ``_classify_cta``.

Wave 5+ Axis 4 follow-through. Mirrors ``test_classifier_eval.py`` for
content_format — runs the cta_type classifier over a hand-curated
golden set and pins:

  * Overall accuracy ≥ MIN_ACCURACY (lower than content_format's
    floor because the cta_type taxonomy is harder: "comment" vs
    "follow" vs "share" boundaries are fuzzy in real CTA copy, where
    creators bundle 2-3 actions per sentence).
  * Recall ≥ MIN_CORE_RECALL on the high-traffic buckets — these
    drive the cta-face-detect audit + downstream report tone.
  * Golden set structural validity (every item has the four required
    fields).

Floor policy mirrors content_format:
  - Floor sits BELOW the current baseline so a single-row regression
    can land while a fix is in flight, but a real classifier
    regression fails CI.
  - Raising the floor after a classifier improvement is fine.
    Lowering it to mask a regression is NOT — fix the regression or
    expand the golden set instead.
"""

from __future__ import annotations

from getviews_pipeline.eval_classifier import evaluate_cta_type, load_cta_type_golden

# Baseline history:
#   2026-05-13 initial harness — 22-item curated set sampled from
#   live corpus + 1 synthesized 'phần 2' row to pin the secondary
#   part2 token branch.
# Floor at 0.80 tolerates ~4 misses on a 22-item set. Tighter than
# the 0.95 content_format floor would over-promise on a fuzzier
# taxonomy where creator CTAs routinely bundle multiple action verbs.
MIN_ACCURACY = 0.80

# Don't regress below this on the high-traffic buckets. ``follow`` +
# ``shop_cart`` + ``try_it`` dominate downstream reports (they're the
# verbs the diagnosis pipeline converts into "the niche's winning CTA
# is X" recommendations) — getting them wrong degrades report quality
# more than misclassifying ``part2`` would.
CORE_CLASSES = {"follow", "shop_cart", "try_it", "save"}
MIN_CORE_RECALL = 0.66  # 2/3 — tolerates one miss on a 3-item bucket


def test_cta_golden_set_loads_and_is_nonempty() -> None:
    items = load_cta_type_golden()
    assert len(items) >= 20, (
        f"Golden set shrank to {len(items)} items — re-growing is fine "
        "but inspection required before loosening the floor."
    )
    for item in items:
        assert "gold_label" in item
        assert "cta_text" in item
        assert "video_id" in item
        # niche_id is informational but pin it so the schema stays
        # consistent for future labelers.
        assert "niche_id" in item


def test_cta_classifier_accuracy_meets_floor() -> None:
    scorecard = evaluate_cta_type()
    assert scorecard.accuracy >= MIN_ACCURACY, (
        f"_classify_cta accuracy {scorecard.accuracy:.4f} below floor "
        f"{MIN_ACCURACY}. Misses:\n"
        + "\n".join(
            f"  {m['video_id']}: gold={m['gold']} pred={m['pred']}"
            f"{(' — ' + m['notes']) if m.get('notes') else ''}"
            for m in scorecard.misses
        )
    )


def test_cta_core_class_recall_is_strong() -> None:
    """High-traffic buckets must stay above MIN_CORE_RECALL. The core
    set covers the verbs most reports surface — a regression here is
    disproportionately expensive."""
    scorecard = evaluate_cta_type()
    bad = {
        cls: round(scorecard.per_class_recall.get(cls, 0.0), 4)
        for cls in CORE_CLASSES
        if scorecard.per_class_recall.get(cls, 0.0) < MIN_CORE_RECALL
    }
    assert not bad, (
        f"Core class recall regressed below {MIN_CORE_RECALL}: {bad}. "
        "Expand the golden set or fix the classifier."
    )


def test_cta_taxonomy_lock() -> None:
    """The golden set's gold_label values must stay inside the 8-label
    universe (7 buckets + 'other'). Catches a typo or rename mistake
    before it pollutes the harness."""
    allowed = {
        "save", "follow", "comment", "shop_cart",
        "link_bio", "part2", "try_it", "other",
    }
    items = load_cta_type_golden()
    bad = [
        i for i in items
        if i["gold_label"] not in allowed
    ]
    assert not bad, f"Off-taxonomy gold labels: {[i['gold_label'] for i in bad]}"


def test_cta_scorecard_structure_is_well_formed() -> None:
    scorecard = evaluate_cta_type()
    d = scorecard.as_dict()
    assert d["total"] > 0
    assert 0.0 <= d["accuracy"] <= 1.0
    # Confusion matrix rows sum to per-gold-class totals.
    from collections import Counter
    gold_counts: Counter[str] = Counter(i["gold_label"] for i in load_cta_type_golden())
    for gold, preds in d["confusion"].items():
        assert sum(preds.values()) == gold_counts[gold]
