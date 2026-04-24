# Viral-Alignment Score — Formula & Calibration Spec

**Status:** Wave 3 PR #5 — design-doc commit (a): spec scaffold.
**Audience:** engineering (to implement Wave 4 score BUILD) + reviewers.
**Related:** `artifacts/docs/implementation-plan.md` Wave 3, the runnable
reference `cloud-run/getviews_pipeline/viral_alignment_backtest.py`
(shipped by Wave 3 PR #4), and the admin trigger
`POST /admin/trigger/viral_score_backtest`.

This commit pins the *proposed* formula + guard rails. The next commit
(b) layers the reproducibility + actual backtest receipts on top; (c)
adds the go/defer verdict. If you're reading this before (b) lands, you
know what we *intend* to score, not what the numbers say.

---

## 1. Purpose

The viral-alignment score answers one specific question:

> *How well does this video align with what's currently winning in its
> niche?*

It explicitly does NOT answer "will this go viral." Virality is
multi-factor (distribution luck, algorithm shifts, creator audience
stickiness) and most of those factors are not observable from the video
itself. We score only the *controllable alignment* — hook / format /
time slot — against the niche's current top-30 performers.

Framing the score this way matters for trust: creators tolerate "you're
out of alignment on hook type" much better than "we predict your video
will flop." The former is a specific, actionable diagnosis; the latter
is a fortune-teller claim.

### Three constraints the formula must respect

1. **No partial scores on sparse niches.** If a niche has < 30
   breakout-scored videos, the formula returns `score=null,
   reason="insufficient_niche_sample"`. A score of 43 on 8 reference
   videos is worse than no score — it implies precision we don't have.
2. **Reasoning is auditable.** Every score ships with 3 Vietnamese
   bullets — one per dimension — explaining the math. These are
   deterministic templates, never Gemini-generated, so a user who
   questions a score can read the actual count (e.g. "9/30 top videos
   dùng hook này"). Non-auditable scores erode trust faster than no
   score.
3. **Score distribution must have meaningful spread.** If 80% of
   production videos land in a single 10-point bin, the score is
   functionally a pass/fail — creators will stop looking at it within
   a week. The backtest (commit b) pins this empirically.

---

## 2. Formula v1 — proposed

```
score = 100 × (w_hook   × hook_alignment
             + w_format × format_alignment
             + w_time   × time_alignment)

hook_alignment   = (# top-30 niche videos with same hook_type)   / 30
format_alignment = (# top-30 niche videos with same content_format) / 30
time_alignment   = 1 - min(1, circular_hour_dist(posting_hour,
                                                 niche_peak_hour) / 6)

w_hook   = 0.5
w_format = 0.3
w_time   = 0.2
```

### Definitions

- **top-30 niche pool:** the 30 video_corpus rows for this niche with
  the highest `breakout_multiplier` (rolling 30-day window).
  `breakout_multiplier` = this video's views / this creator's own
  trailing-average views, so "top breakout" means "punched above the
  creator's baseline" — a measure of alignment fit, not raw popularity.
- **hook_type / content_format matching:** exact-string equality against
  the canonical enum values (no fuzzy matching; the ingest path
  already normalizes via `_HOOK_TYPE_ALIASES`).
- **circular_hour_dist:** `min(|a − b|, 24 − |a − b|)`. Makes 23h vs 0h
  a 1-hour gap, not 23. Clock wraps.
- **niche_peak_hour:** mode of `posting_hour` across the niche's
  top-30 pool. Deterministic; tie-break by earliest hour.

### Weights rationale (initial, to be calibrated)

The 0.5 / 0.3 / 0.2 split leans on hook because hook is the
single-highest-signal dimension the Gemini analysis extracts — it drives
first-frame retention which gates everything downstream. Format weight
is secondary because format alignment within a niche is a weaker
discriminator (two "review" videos can differ wildly in execution).
Time is a tiebreaker, not a driver — ratio 2.5:1.5:1 across dimensions.

Commit (b) reports the correlation of each dimension *in isolation*
against breakout_multiplier, which is the input to the calibration
loop.

---

## 3. Top-30 reference pool — edge cases

- **Sample video in its own top-30:** we still score against the full
  top-30 including self. The 1/30 self-reference bias is negligible
  and keeping the denominator fixed at 30 avoids a subtle "my score
  changed after I got popular" surprise for creators.
- **Ties at rank 30:** stable tie-break by `video_id` (lexical). A
  deterministic pool matters for reproducibility — the backtest (b)
  seeds both the sample *and* the pool.
- **Missing dimension on a pool video:** a pool row with `hook_type =
  NULL` can't contribute to `hook_alignment` — it's counted as a
  non-match (denominator stays 30). We do not drop the row from the
  pool; its other dimensions are still informative.

---

## 4. Low-sample graceful degradation

```python
if len(niche_top30) < 30:
    return ViralScoreResult(score=None, insufficient_reason="insufficient_niche_sample")
if inputs.hook_type is None:
    return ViralScoreResult(score=None, insufficient_reason="missing_hook_type")
if inputs.content_format is None:
    return ViralScoreResult(score=None, insufficient_reason="missing_content_format")
```

Three distinct reason strings, not one — the FE pill renders different
copy per case:

| reason                        | Vietnamese copy                                            |
|-------------------------------|------------------------------------------------------------|
| `insufficient_niche_sample`   | "Chưa đủ video tham chiếu trong ngách (cần ≥ 30)."         |
| `missing_hook_type`           | "Chưa phân loại được hook — bỏ qua điểm alignment."        |
| `missing_content_format`      | "Chưa phân loại được format — bỏ qua điểm alignment."      |

The `posting_hour = NULL` case does NOT null the whole score — only the
time dimension contributes 0. This is the one partial-score
concession: hook + format together still convey most of the signal, and
80% of legacy corpus rows pre-date the posting_hour backfill. A null
whole-score on those would break the surface for half the corpus.

---

## 5. Reasoning bullets spec

Every non-null score ships with exactly 3 bullets — one per dimension,
in this order:

1. **Hook:**  `"Hook {hook_type!r}: {N}/30 top video ngách dùng cùng kiểu."`
2. **Format:** `"Format {content_format!r}: {N}/30 top video ngách cùng định dạng."`
3. **Time:** one of:
   - `"Đăng đúng giờ đỉnh của ngách ({peak}h)."`  (diff == 0)
   - `"Đăng lệch {N}h so với giờ đỉnh ngách ({peak}h)."`  (diff > 0)
   - `"Chưa có giờ đăng — bỏ qua tín hiệu thời điểm."`  (NULL peak or posting_hour)

All three are deterministic Python f-strings. Gemini is never involved —
a reasoning bullet must be re-derivable from the score alone, or users
can't fact-check it.

Bullets are NOT prose paragraphs. Each is ≤ 1 line, data-first. This is
deliberately tight to fit the brutalist-card chip pattern already used
by the diagnosis execution-tip callout (Wave 3 PR #2).

---

## 6. What this spec does NOT cover yet

- **Score-to-tier mapping** (e.g. 80+ = green, 50-79 = amber, 0-49 =
  red). Tier thresholds must be chosen AFTER the backtest so the bands
  reflect the actual distribution, not guess-work. Commit (b) reports
  the distribution; commit (c) either proposes thresholds or defers.
- **Go/defer verdict for Wave 4 BUILD.** The plan's exit criteria is
  Spearman ρ ≥ 0.35 between score and `breakout_multiplier` on a
  200-video sample. Whether we clear the gate is commit (c)'s call.
- **Display-side design** (pill placement, copy, animation). Design-
  system territory once the formula is signed off.

These three sections land in commits (b) and (c).

---

## 7. Backtest — methodology

All numbers below come from running
`viral_alignment_backtest.run_viral_score_backtest(client, seed=2026)`
against production `video_corpus` on 2026-04-24. The harness is the
runnable reference for this doc — any time the formula or its
parameters change, re-running the harness produces the new receipts.

### 7.1 Data filter

```
WHERE breakout_multiplier IS NOT NULL
  AND niche_id           IS NOT NULL
  AND hook_type          IS NOT NULL
  AND content_format     IS NOT NULL
```

Only rows with a ground-truth `breakout_multiplier` + the two required
formula inputs are scoreable. `posting_hour = NULL` rows stay in (time
dim contributes 0) to reflect the production surface.

### 7.2 Sample

Corpus at backtest time: 1,548 rows total. After the filter above:
**515 rows** across 20 niches; **352 rows** fall into the 8 niches
with ≥ 30 breakout-scored videos (the other 12 niches trigger
`insufficient_niche_sample`).

For this backtest we score **all 352 eligible rows** rather than the
plan's 200-sample subset — larger n tightens the Spearman confidence
interval (95% CI on ρ narrows from ±0.14 at n=200 to ±0.11 at n=352)
and costs nothing extra in this seeded run.

### 7.3 Reproducibility

- **Seed:** 2026 (default in `AdminTriggerViralScoreBacktestBody`).
  The harness passes it to `random.Random(seed)` so niche ordering
  and sample selection are byte-stable across runs.
- **Backtest source:** deterministic SQL equivalent of the Python
  harness, pinned below. Both paths produce the same ρ to 4 decimals.
- **Admin trigger:** `POST /admin/trigger/viral_score_backtest` writes
  `batch_job_runs` with `job_name='viral_score_backtest'` so the
  committed numbers remain auditable post-deploy.

---

## 8. Backtest — results

### 8.1 Headline: Spearman ρ vs breakout_multiplier

| Formula variant                                   |      ρ |     n |
|---------------------------------------------------|-------:|------:|
| **V1 spec (0.5 hook / 0.3 format / 0.2 time)**    | **0.141** | 352 |
| Format-heavy (0.15 / 0.70 / 0.15)                 |  0.176 | 352 |

Plan's exit-criteria gate: **ρ ≥ 0.35**. Neither variant clears it.

### 8.2 Per-dimension Spearman ρ (each dimension alone)

| Dimension              |      ρ |
|------------------------|-------:|
| format_alignment       |  0.169 |
| time_alignment         |  0.073 |
| hook_alignment         |  0.050 |

`format` carries nearly all the signal. `hook` is the highest-weighted
dimension in V1 but contributes essentially noise — re-weighting to
format-heavy recovers `format_alone`'s ρ almost exactly, which is why
V1 underperforms its own format dimension.

### 8.3 Additional candidate dimensions

Tested for inclusion in a V2 formula (all as "match against top-30 of
same field" alignments, except text_overlays and duration which use
raw-value ranks):

| Dimension          |      ρ |
|--------------------|-------:|
| creator_tier       |  0.058 |
| tone               |  0.046 |
| video_duration     |  0.043 |
| first_frame_type   |  0.016 |
| text_overlay_count |  0.016 |

None of them move the needle. A Wave-4-scale formula built on these
would not clear the gate either.

### 8.4 Score distribution (V1 formula, all 352 rows)

| Statistic | Value  |
|-----------|-------:|
| min       |   4    |
| p10       |  16    |
| p25       |  25    |
| median    |  33.5  |
| mean      |  33.25 |
| p75       |  42    |
| p90       |  49    |
| max       |  66    |
| stddev    |  12.95 |

The distribution has meaningful spread (IQR = 17, stddev 13) — no
"everyone gets 70–80" clustering, which was the reviewer's specific
worry. But the mean sits at 33: with the weighted formula, a "perfect
alignment" video on a typical niche scores in the 60s (because no
single hook_type holds 100% of a niche's top-30). The V1 math is
internally consistent; it's the predictive power that's missing, not
the spread.

### 8.5 Quintile lift

Videos bucketed into 5 equal-sized score quintiles, then measured
against their actual `breakout_multiplier`:

| Quintile | n  | score range | median breakout | mean breakout |
|---------:|---:|:------------|----------------:|--------------:|
| Q1       | 71 |  1–20       | 0.550           | 0.646         |
| Q2       | 71 | 20–29       | 0.870           | 1.047         |
| Q3       | 70 | 29–37       | 0.705           | 0.892         |
| Q4       | 70 | 37–45       | 0.795           | 0.891         |
| Q5       | 70 | 45–66       | 0.970           | 0.978         |

Tail discrimination works: Q1 (lowest-scoring fifth) has median
breakout 0.55 vs Q5's 0.97 — a 1.76× lift at the extremes. Middle
quintiles (Q2–Q4) are non-monotone — Q2 median (0.87) is actually
higher than Q3 (0.71). Which is where the ρ = 0.14 hurts: *most*
production videos would land in Q2–Q4 where the score can't
reliably order them.

A score that only discriminates at the tails is not a useful UI pill
— creators don't self-select into "obviously-bad" or "obviously-good"
video shots. They want the score to guide the 80% of videos in the
middle, which is exactly where V1 fails.

### 8.6 Insufficient-data rate

Of the 515 rows meeting the formula's minimum field requirements
(hook_type + content_format + breakout_multiplier present), **32%
(163 rows) fall into niches below the 30-row threshold**. In
production, one in three scored submissions would see the
insufficient_niche_sample null path.

That's a graceful-degradation test we do pass — the helper returns
`null + reason`, the FE surface would render a "Chưa đủ video tham
chiếu" chip, and the rest of the diagnosis carries on. But combined
with the weak ρ on the remaining 68%, the net useful-score rate is
low.

Commit (c) weighs these numbers against the ρ ≥ 0.35 gate and makes
the go/defer call.
