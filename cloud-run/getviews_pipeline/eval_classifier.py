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
_HOOK_TYPE_GOLDEN_PATH = Path(__file__).parent / "eval_data" / "hook_type_golden.json"
_CTA_TYPE_GOLDEN_PATH = Path(__file__).parent / "eval_data" / "cta_type_golden.json"


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


# ── cta_type eval (CI-safe — pure-function classifier) ────────────────


def load_cta_type_golden() -> list[dict[str, Any]]:
    """Load the cta_type golden set from disk.

    Each item: ``video_id`` (str, traceability), ``niche_id`` (int,
    traceability — NOT consumed by the classifier), ``cta_text`` (str,
    the input ``_classify_cta`` reads), ``gold_label`` (one of the 7
    bucket labels or ``"other"``), ``notes`` (free-form rationale).
    """
    with _CTA_TYPE_GOLDEN_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return list(payload.get("items") or [])


def evaluate_cta_type(
    items: list[dict[str, Any]] | None = None,
) -> EvalScorecard:
    """Run ``_classify_cta`` over the golden set and return a scorecard.

    Symmetric with ``evaluate()`` for content_format — pure-function
    classifier, CI-safe, no DB / Gemini dependency.
    """
    from getviews_pipeline.corpus_ingest import _classify_cta

    if items is None:
        items = load_cta_type_golden()

    scorecard = EvalScorecard()
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in items:
        gold = item["gold_label"]
        # _classify_cta returns ``None`` for empty input + ``"other"``
        # for non-matching text. Coerce a None pred into the literal
        # "none" bucket so the confusion matrix doesn't lose rows.
        pred_raw = _classify_cta(item.get("cta_text"))
        pred = pred_raw if pred_raw is not None else "none"

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


# ── hook_type eval (DB-backed; NOT CI-safe) ───────────────────────────

def load_hook_type_golden() -> list[dict[str, Any]]:
    """Load the hook_type golden set from disk.

    Unlike ``content_format`` (where the classifier runs locally from
    ``analysis_json``), ``hook_type`` is emitted directly by Gemini at
    extraction time. Items therefore don't carry a full ``analysis_json``
    snapshot — just ``video_id``, ``niche_id``, ``hook_phrase``,
    ``transcript_snippet`` (for human review), and ``gold_label``.
    """
    with _HOOK_TYPE_GOLDEN_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return list(payload.get("items") or [])


def evaluate_hook_type(
    items: list[dict[str, Any]] | None = None,
    *,
    client: Any | None = None,
) -> EvalScorecard:
    """Measure production hook_type accuracy against the golden set.

    Reads current ``video_corpus.hook_type`` for each golden ``video_id``
    and compares to the hand-assigned ``gold_label``. **Requires DB
    access** — do not call from CI. For CI-safe structural checks,
    see ``tests/test_hook_type_eval.py`` (separate commit).

    Missing rows (golden video_id not in live corpus) are tracked as
    ``misses`` with ``pred=None`` but NOT counted against accuracy —
    they represent corpus churn, not classification error.
    """
    from getviews_pipeline.supabase_client import get_service_client

    if items is None:
        items = load_hook_type_golden()
    if client is None:
        client = get_service_client()

    # Fetch all hook_types in one query (≤50 items, well under PostgREST limit).
    video_ids = [str(i["video_id"]) for i in items]
    resp = (
        client.table("video_corpus")
        .select("video_id, hook_type")
        .in_("video_id", video_ids)
        .execute()
    )
    db_labels: dict[str, str | None] = {
        r["video_id"]: r.get("hook_type") for r in (resp.data or [])
    }

    scorecard = EvalScorecard()
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in items:
        gold = item["gold_label"]
        vid = str(item["video_id"])
        pred = db_labels.get(vid)

        if pred is None:
            # Row missing from corpus (deleted / never ingested).
            # Don't penalize accuracy — track as a separate miss category.
            scorecard.misses.append({
                "video_id": vid,
                "gold": gold,
                "pred": None,
                "notes": "row not found in video_corpus (corpus churn, not classifier error)",
            })
            continue

        scorecard.total += 1
        confusion[gold][pred] += 1

        if pred == gold:
            scorecard.correct += 1
            tp[gold] += 1
        else:
            fp[pred] += 1
            fn[gold] += 1
            scorecard.misses.append({
                "video_id": vid,
                "gold": gold,
                "pred": pred,
                "notes": item.get("notes"),
            })

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
