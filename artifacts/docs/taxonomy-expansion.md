# content_format Taxonomy Expansion — Design Spec

**Status:** Wave 5+ design-doc commit (a): scaffold.
**Audience:** engineering (to implement if greenlit) + reviewers.
**Related:** `artifacts/docs/implementation-plan.md` Wave 5+, the
`classify_format` TAXONOMY LOCK docstring in
`cloud-run/getviews_pipeline/corpus_ingest.py:564`, and the Wave 5+
expanded eval harness at `tests/test_classifier_eval.py` (54-item
golden set, MIN_ACCURACY=0.88).

This commit pins the *what-for* and *what's-in-the-way* before commit
(b) proposes buckets and commit (c) specs the build. If you're
reading this before (b) lands, you know the decision being made, not
the outcome.

---

## 1. The problem

`video_corpus.content_format` is a 15-value taxonomy. **37% of rows
(669/~1,830) land in the `other` catch-all** because they don't fit
any bucket. The `other` residual is concentrated in a handful of
niches:

| niche | other rows | dominant tone |
|---|---:|:---|
| 17 (Gaming / esports)         |  82 | entertaining |
| 13 (Comedy / entertainment)   |  82 | humorous |
| 6  (Aspirational lifestyle)   |  76 | entertaining |
| 11 (Education)                |  62 | educational |
| 16 (Travel / tourism)         |  57 | entertaining |
| 8  (Fitness / gym)            |  50 | educational |
| 21 (Sports / outdoor)         |  38 | entertaining + inspirational |

Downstream consequence: `niche_intelligence.format_distribution` —
the JSONB aggregate that feeds Pattern + Ideas + Diagnosis reports —
shows `other: 37%` for nearly every niche. The reports' "top format
in your niche" insight degrades to "most videos don't fit any
category we track", which is accurate but unactionable.

---

## 2. Two paths (the decision)

**Path A — Expand the taxonomy.** Add 3-5 new buckets covering the
dominant "other" patterns (gaming, comedy skits, educational content
the tutorial regex misses, short highlight clips). Commit (b)
proposes the exact bucket list + per-bucket heuristics.

  - **Benefit:** `other` drops from 37% → ~19% (estimated on the
    current corpus; commit (b) pins the rough-cut numbers). Reports
    gain a meaningful "top format" insight for the gaming / comedy /
    education-heavy niches.
  - **Cost:** atomic 7-layer refactor. The TAXONOMY LOCK docstring
    enumerates the impacted files (corpus_ingest, output_redesign's
    FORMAT_ANALYSIS_WEIGHTS, gemini.py prompt injection,
    layer0_niche, layer0_migration, niche_intelligence
    materialized-view, prompts.py). Plus a SQL backfill on the live
    corpus — stale `content_format` values silently fall through to
    the `other` branch of FORMAT_ANALYSIS_WEIGHTS, degrading
    diagnosis prompts until the UPDATE runs.

**Path B — Accept `other` as terminal.** Document that the residual
is a product-wide known-unknown; surface "other" explicitly in
reports as "không có công thức chính" instead of mis-branding it.
Zero code change.

  - **Benefit:** no migration risk. The taxonomy stays small + stable.
  - **Cost:** the 37% residual persists. Reports for gaming / comedy
    / education niches stay light on the "top format" dimension,
    which is the niche's most intuitive slot.

**Recommendation (this doc):** Path A, but scoped. Commit (b)
proposes 4 buckets — gameplay, comedy_skit, lesson, highlight — that
rough-cut to ~48% of the current `other` residual. The remaining
~52% stays `other` because forcing heterogeneous content into false
labels would degrade downstream reports more than the `other`
residual does. Commit (c) estimates the effort (~1 week) + pins the
exit criteria.

---

## 3. The taxonomy-lock constraint

From `classify_format` docstring — the 7 call sites that read
`content_format` and how each reacts to an unknown value:

| Layer | What it does with `content_format` | Failure mode on unknown |
|---|---|---|
| `corpus_ingest.py` | writes it into the DB column | new value lands in DB, no crash |
| `output_redesign.py` `FORMAT_ANALYSIS_WEIGHTS` | switch table: per-format signal weights for the diagnosis prompt | unknown key → fallback to `other` weights; degrades diagnosis framing silently |
| `gemini.py` | passes format string into the synthesis prompt context | Gemini sees a word it hasn't been shown examples for; no hard break but quality drops |
| `layer0_niche.py` | aggregates "top hook × top format" per week | unknown value dilutes the formula-detection ranking |
| `layer0_migration.py` | groups migration signals by week × format | unknown value creates a new ungrouped bucket in the output |
| `niche_intelligence` MV | `format_distribution` JSONB aggregation | unknown value surfaces in the %-distribution |
| `prompts.py` | format_distribution injected into corpus-citation blocks | Gemini reads the new key; no-op unless the string is gibberish |

**Atomic change requirement:** adding a new bucket means touching all
7 layers AND running a SQL backfill on existing rows in one migration
window. Skipping the backfill leaves old rows at `other` permanently;
skipping a code layer leaves that layer's behaviour undefined on
new-bucket rows.

**Pre-check:** commit (c) specifies "add new values to
FORMAT_ANALYSIS_WEIGHTS FIRST, run the migration + backfill SECOND,
then update `classify_format` THIRD" — the docstring's own
prescription, which we honor here.

---

## 4. Related prior work (learned from)

- **Wave 0 `content_format_reclassify.py`** — already does a SQL
  catch-up from `other` → detected bucket when a regex tweak adds a
  new signal. Same code path we'd reuse for the taxonomy-expansion
  backfill; no new tooling needed.
- **Wave 5+ content_format golden set** — just landed at 54 items /
  0.907 accuracy / 0.88 floor. Commit (c) specs adding ~3 golden
  items per new bucket (12-15 total) so the eval harness locks the
  new buckets' accuracy from day one.
- **Wave 3 viral-alignment-score design doc** — structurally what
  this doc mirrors. That doc said "backtest first, decide after"; we
  do the same: commit (b) proposes buckets, commit (c) sets the
  exit criteria (accuracy floor, `other` residual shrink), a
  follow-up implementation PR would then run the backfill and
  measure against the criteria.

---

## 5. What this spec does NOT cover yet

- **Exact bucket labels + per-bucket heuristics.** Commit (b).
- **Implementation effort + backfill plan + validation gates.**
  Commit (c).
- **Gemini-classification alternative.** The classify_format
  docstring called out a deferred proposal (M.8) to replace regex
  with Flash-Lite classification. That's out of scope here — this
  doc proposes regex-heuristic expansions only, same deterministic
  model. A separate design doc is needed if the regex path saturates.
- **Per-niche taxonomy.** Some new buckets (gameplay) are niche-
  specific. Whether to gate them by niche_id (like the existing
  mukbang niche=4 heuristic) or keep them global is a bucket-level
  decision in commit (b).

These three sections land in commits (b) and (c).
