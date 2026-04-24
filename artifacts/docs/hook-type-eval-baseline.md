# hook_type eval harness — baseline audit

**Date:** 2026-05-10
**Scope:** Wave 1 PR #4 of the revised implementation plan.
**Purpose:** close the plan's Wave 2 prerequisite — measure Gemini's `hook_type` classification accuracy on a hand-labeled held-out set before Ideas ("5 video tiếp theo") builds on top of it.

---

## TL;DR

- **Baseline: 28/31 = 0.903 accuracy.** Clears the 0.85 floor comfortably.
- **hook_type is reliable enough for Wave 2.** No Wave 1.5 prompt-engineering detour required.
- **3 misses surfaced** — 2 are "none vs other" edge-case ambiguity, 1 is a real Gemini miss (song lyrics → question) worth queuing as future prompt work.
- CI gate lives in `cloud-run/tests/test_hook_type_eval.py` — 4 structural checks always, live-accuracy check skipped unless `SUPABASE_SERVICE_ROLE_KEY` is set.

---

## Method

### Golden set: 31 items

Hand-labeled from live `video_corpus` rows with **no reference to `video_corpus.hook_type`** (labels assigned by reading `hook_phrase` + `audio_transcript` directly). Every label carries a rationale in `notes` for future re-labeling passes.

| Bucket | # items |
|---|---|
| `how_to` | 4 |
| `bold_claim` | 3 |
| `story_open` | 3 |
| `pain_point` | 3 |
| `none` | 3 |
| `curiosity_gap` | 2 |
| `question` | 2 |
| `social_proof` | 2 |
| `challenge` | 2 |
| `trend_hijack` | 2 |
| `controversy` | 2 |
| `shock_stat` | 2 |
| `other` | 1 |

All 13 labels that appear in the live corpus are covered (≥2 each except `other` which is intentionally narrow). The 6 additional normalizer-mapped labels (`warning`, `price_shock`, `reaction`, `comparison`, `expose`, `pov`) are omitted — Gemini has never emitted them in production.

### Runner

`evaluate_hook_type()` in `cloud-run/getviews_pipeline/eval_classifier.py`:

1. Reads every golden item's `video_id`.
2. One Supabase query: `SELECT video_id, hook_type FROM video_corpus WHERE video_id IN (...)`.
3. Compares DB `hook_type` to gold `gold_label`.
4. Missing rows (corpus churn / deletion) tracked as misses with `pred=None` but NOT counted against accuracy.
5. Returns the same `EvalScorecard` dataclass used by `content_format`.

---

## Baseline results (2026-05-10)

```
total:    31
correct:  28
accuracy: 0.9032
misses:   3
```

### Misses

| video_id | gold | Gemini pred | verdict |
|---|---|---|---|
| `7622274736667544852` | `how_to` | `none` | **Real miss.** Makeup tutorial opens with "The first thing I'm going to do is I'm going to take my concealer" — textbook step-1 how_to framing. Gemini returned `none`. |
| `7618983118342606101` | `none` | `other` | **Edge-case ambiguity.** Puppy howl, no speech, no hook. Gold = `none` (reserved for no-hook). Gemini chose `other`. The distinction is documented in the golden rubric but not a production-critical error. |
| `7629201473049529621` | `none` | `question` | **Real miss.** Vietnamese song lyrics "Nằm mơ sáu mươi năm cuộc đời..." contain zero questions. Gemini wrongly labeled it `question`. |

Net: 1 edge-case disagreement + 2 real Gemini misses. The real misses are not a blocker — a future prompt-engineering pass can tighten `how_to` recognition on English tutorial openings and `none` vs. `question` disambiguation on lyric-heavy videos.

---

## CI gate

### `cloud-run/tests/test_hook_type_eval.py`

- **Always runs (CI-safe):**
  1. Golden set loads and has ≥ 25 items.
  2. Every `gold_label` is in the 13-label taxonomy.
  3. Every item has the required fields (`video_id`, `niche_id`, `gold_label`, `hook_phrase`, `transcript_snippet`).
  4. Every item has non-empty `notes` (rationale for future re-labeling).

- **Conditional (gated on `SUPABASE_SERVICE_ROLE_KEY`):**
  5. `test_live_hook_type_accuracy_meets_floor` — fails the build if live accuracy drops below `MIN_ACCURACY = 0.85`.

### Floor policy

- Current baseline **0.903** → floor **0.85** tolerates exactly one additional regression before failing.
- Future improvements that raise accuracy → raise the floor in a separate PR, commit message explaining the new baseline. **Never lower the floor to mask a regression** — fix the regression or expand the golden set.

---

## What did NOT ship in this PR

- **No production reclass.** 31 items aren't enough to justify a batch reclass of the whole corpus; the next eval pass (likely expanded to 60+ items in Wave 5+) would inform that decision.
- **No Gemini prompt changes.** Two real misses identified but not fixed — they're small enough that Wave 2 can proceed safely; future prompt work lives on its own PR.
- **No admin trigger.** The eval runs manually (`python -c "from getviews_pipeline.eval_classifier import evaluate_hook_type; ..."`) or via the CI hook. An admin-triggered historical eval can layer on top later.

---

## Related

- State-of-corpus Axis 4 (`artifacts/docs/state-of-corpus.md`): the "zero golden set, zero eval harness" finding that motivated this track.
- Implementation plan Wave 1 (`artifacts/docs/implementation-plan.md`): this PR closes the `hook-type-eval-harness` item that gates Wave 2.
- Content_format counterpart (`artifacts/docs/cta-face-detect-audit.md`, `cloud-run/getviews_pipeline/eval_data/content_format_golden.json`): same harness shape for the locally-replayable classifier.
