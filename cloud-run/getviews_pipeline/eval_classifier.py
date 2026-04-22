"""Eval harness for ``classify_format``.

Closes the Axis 4 gap (state-of-corpus.md): no golden set, no accuracy
tracking, no regression test. Without this, every classifier change is
a leap of faith — "did that regex tweak help or hurt?" is unanswerable.

This is the V1 harness:

  - A JSON golden file (`eval_data/content_format_golden.json`) with
    hand-curated (video_id, analysis_json, gold_label) tuples. Labels
    ignore the live DB's noisy ``content_format`` values; they were
    assigned by reading transcripts directly.
  - ``evaluate(golden_items)`` runs the classifier over every item
    and returns a scorecard: overall accuracy, per-class precision /
    recall, and the full confusion matrix.
  - The pytest integration (``tests/test_classifier_eval.py``) pins
    a minimum accuracy floor, so any PR that regresses below that
    floor fails CI.

Future extensions (deliberately out of scope for V1):
  - Persist eval runs to a DB table for history / trend tracking.
  - Multi-classifier harness (hook_type, cta_type, content_format).
  - Active-learning loop to grow the golden set as labelers review
    classifier-uncertain rows.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_GOLDEN_PATH = Path(__file__).parent / "eval_data" / "content_format_golden.json"


@dataclass
class EvalScorecard:
    total: int = 0
    correct: int = 0
    per_class_precision: dict[str, float] = field(default_factory=dict)
    per_class_recall: dict[str, float] = field(default_factory=dict)
    per_class_f1: dict[str, float] = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    misses: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "per_class_precision": {k: round(v, 4) for k, v in self.per_class_precision.items()},
            "per_class_recall": {k: round(v, 4) for k, v in self.per_class_recall.items()},
            "per_class_f1": {k: round(v, 4) for k, v in self.per_class_f1.items()},
            "confusion": self.confusion,
            "miss_count": len(self.misses),
        }


def load_golden() -> list[dict[str, Any]]:
    """Load the golden set from disk. Raises FileNotFoundError if missing."""
    with _GOLDEN_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return list(payload.get("items") or [])


def evaluate(
    items: list[dict[str, Any]] | None = None,
) -> EvalScorecard:
    """Run ``classify_format`` over the golden set and return a scorecard.

    Each item must have: ``analysis_json`` (dict), ``niche_id`` (int),
    ``gold_label`` (str). Optional: ``video_id``, ``notes``.
    """
    from getviews_pipeline.corpus_ingest import classify_format

    if items is None:
        items = load_golden()

    scorecard = EvalScorecard()
    # true_positives[label] = count of rows whose gold == label AND pred == label
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()   # pred == label, gold != label
    fn: Counter[str] = Counter()   # gold == label, pred != label
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in items:
        gold = item["gold_label"]
        pred = classify_format(item["analysis_json"], int(item["niche_id"]))

        scorecard.total += 1
        confusion[gold][pred] += 1

        if pred == gold:
            scorecard.correct += 1
            tp[gold] += 1
        else:
            fp[pred] += 1
            fn[gold] += 1
            scorecard.misses.append({
                "video_id": item.get("video_id"),
                "gold": gold,
                "pred": pred,
                "notes": item.get("notes"),
            })

    # Precision / recall per class.
    classes = set(tp) | set(fp) | set(fn)
    for cls in classes:
        p_denom = tp[cls] + fp[cls]
        r_denom = tp[cls] + fn[cls]
        precision = tp[cls] / p_denom if p_denom else 0.0
        recall = tp[cls] / r_denom if r_denom else 0.0
        f1_denom = precision + recall
        f1 = 2 * precision * recall / f1_denom if f1_denom else 0.0
        scorecard.per_class_precision[cls] = precision
        scorecard.per_class_recall[cls] = recall
        scorecard.per_class_f1[cls] = f1

    scorecard.confusion = {k: dict(v) for k, v in confusion.items()}
    return scorecard
