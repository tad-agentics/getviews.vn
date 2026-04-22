# State of the Corpus — baselining the asset

**Prepared:** 2026-04-22 (DB `NOW()`)
**Purpose:** establish concrete numbers along the 5 quality axes that define
the visual-intelligence data asset underneath the GetViews app. This
baselines the moat. Once we know where we are, we can plan where to go.

**Intended re-run cadence:** weekly. The SQL used to produce every number
below is inline so this can be regenerated without recovering context.

---

## Executive summary

The corpus is **genuinely Vietnamese-first and fresh** — every single
video was posted in the last 90 days, ~95% in the last 30, and ~42% in
the last 7. Ingestion delay (posted → indexed) averages 5 days. That's
the good news and it validates the direction.

The bad news is scale and discipline:

| Axis | Current state | Gap |
|---|---|---|
| **1. Coverage** | 1,220 videos across 21 niches. Max 128, median ~50, min 6. **Corpus growth is 100% manual today** — no data-pipeline cron exists ([Appendix B · Gap 4](#gap-4--no-weekly-cron-for-data-quality-jobs--confirmed-worse)). | Every niche is below the 500-video "exceptional" floor. Top-of-funnel is a bottleneck. Landing-page marketing copy claims "46.000+ videos" — **off by 37×.** |
| **2. Analysis depth** | 100% of rows have hook_type + tone + scene_count. But 37% bucket to `content_format = 'other'` (catch-all) and only 30% have `cta_type`. `breakout_multiplier`: **0 of 1,220 rows**. Downstream: **`hook_effectiveness` aggregate table has 0 rows in prod** — Pattern + Ideas reports render with empty hook findings ([Gap 1](#gap-1--hook_effectiveness-empty-in-prod--confirmed-worse)). | Classifiers are coarse, one declared signal is dead, and the aggregate table every report queries has never been populated. |
| **3. Freshness** | Corpus is 12 days old total. Views/likes/engagement stamped once at ingest and never refreshed. No `updated_at` column. **Freshness holds only because someone runs ingest by hand** — no scheduled trigger. | Trend detection runs on stale view counts. A video that went viral post-ingest is invisible to our scoring. And the freshness we have is manual-effort-bound, not system-guaranteed. |
| **4. Quality measurability** | **Zero golden set. Zero eval harness.** No accuracy tracking. No confidence scores stored per classification. No commit-over-commit regression testing on classifier output. | We can't answer "did this pipeline change make the data better or worse?" |
| **5. Observability** | `batch_failures` table exists, has 0 rows, and **no code path writes to it.** No `success` column on `gemini_calls`. **Zero data-pipeline crons exist** — 4 cron jobs are scheduled but all are operational (expiry, credit reset, etc.), none touch the corpus. No daily-health digest. | There is no pipeline to observe. Silent failure surface isn't "big" — the whole data-pipeline surface is off-schedule. |

**The meta-finding:** we've built a pipeline but we haven't built a
**quality discipline around the pipeline**. The Appendix B verification
makes this concrete: the aggregate table every Answer report queries
(`hook_effectiveness`) has never been written to; the insight table
video-diagnosis references (`niche_insights`) hasn't been refreshed in
9+ days; and no cron in the project pulls the pipeline forward. The
discipline is what a data company has and a SaaS app doesn't. Closing
that gap is the moat.

---

## Axis 1 — Coverage breadth (per-niche)

### Current state

Total rows in `video_corpus`: **1,220**. Distinct niches represented:
**21**. The `niche_taxonomy` table has 21 rows, so coverage is
niche-wide — no niche is entirely missing. But the distribution is
thin everywhere:

| Niche | Videos | Fresh ≤7d |
|---|---|---|
| Review đồ ăn / F&B | 128 | 60 |
| Làm đẹp / Skincare | 113 | 51 |
| Gym / Fitness & Sức khoẻ | 106 | 55 |
| EduTok VN | 96 | 59 |
| Hài / Giải trí | 84 | 64 |
| Gaming | 79 | 60 |
| Tài chính / Đầu tư | 75 | 59 |
| Du lịch / Travel | 65 | 49 |
| Chị đẹp | 64 | 46 |
| Mẹ bỉm sữa / Parenting | 56 | 28 |
| Thể thao & Ngoài trời | 50 | 50 |
| Bất động sản | 49 | 26 |
| Review đồ Shopee / Gia dụng | 43 | 13 |
| Ô tô / Xe máy | 38 | 27 |
| Nấu ăn / Công thức | 35 | 35 |
| Thời trang / Outfit | 31 | 15 |
| Công nghệ / Tech | 30 | 15 |
| Shopee Live / Livestream | 30 | 10 |
| Thú cưng | 29 | 29 |
| Kiếm tiền online / MMO | 13 | 8 |
| Nhà cửa / Nội thất | 6 | 6 |

**Everything is fresh_30d = total** (corpus didn't exist >30 days ago).
All niches were touched in the last 0–1 day → cron (or equivalent) is
active. But:

- **21 of 21 niches are below a 500-video "exceptional" floor.** The
  top niche has 26% of the floor; the median sits at ~10%; the smallest
  (Nhà cửa / Nội thất) has 1.2%.
- **5 niches have <35 videos** — below the thin-corpus gate
  `LIFECYCLE_SAMPLE_FLOOR = 80` we enforce in lifecycle reports and
  `TIMING_SAMPLE_FLOOR = 80`. Any user in those niches gets
  fixture-fallback or "MẪU MỎNG" UI everywhere.
- **Landing-page marketing claims "46.000+ videos" — actual is 1,220,
  off by ~37×.** Separate issue from corpus health but worth flagging
  for legal / trust hygiene.

### Gap to exceptional

| Target | Reason |
|---|---|
| **Every active niche ≥500 videos** | Below this, per-format aggregates (e.g. `compute_format_cells`) produce noisy cells. 500 was the timing/lifecycle floor we agreed on. |
| **Per-niche SLA enforced by cron** | If a niche drops below floor, a backfill cron re-fetches. Today: no enforcement, no alert. |
| **Total corpus ≥20K rolling 30-day** | Proxy for "comparable to a real data asset." Current 1,220 is an order of magnitude short. |
| **Marketing copy matches reality** | Either land the 46K claim by scaling, or change the copy. |

### What it takes to close

1. **Audit the ingest trigger**: today there's no cron in
   `supabase/functions/` that runs `corpus_ingest`. It's invoked by
   hand or via a Cloud Run batch. We need a scheduled trigger with
   observable output.
2. **Per-niche backfill logic**: `corpus_ingest` currently pulls the
   same shape every run. It needs a "which niche is thinnest, prioritise
   that one" heuristic.
3. **Rate-limit / cost model**: EnsembleData + Gemini costs per video
   are measurable (see Axis 5). At $0.003/call average Gemini spend, a
   push from 1,220 → 20K is ~$60. Not the blocker. Ingestion speed is.

### SQL used

```sql
-- Per-niche counts, freshness, last ingest
WITH niche_stats AS (
  SELECT niche_id, COUNT(*) AS total,
         COUNT(*) FILTER (WHERE indexed_at > NOW() - INTERVAL '7 days')  AS fresh_7d,
         COUNT(*) FILTER (WHERE indexed_at > NOW() - INTERVAL '30 days') AS fresh_30d,
         MAX(indexed_at) AS last_ingest
  FROM public.video_corpus GROUP BY niche_id
)
SELECT t.name_vn AS niche, s.total, s.fresh_7d, s.fresh_30d,
       EXTRACT(DAY FROM NOW() - s.last_ingest)::int AS days_since_last_ingest
FROM niche_stats s LEFT JOIN public.niche_taxonomy t ON t.id = s.niche_id
ORDER BY s.total DESC;
```

---

## Axis 2 — Analysis depth per video

### Current state

Every row in `video_corpus` is supposed to go through extraction
(regex classifiers + Gemini vision). Completeness by field:

| Field | Populated | % | Notes |
|---|---|---|---|
| `hook_type` | 1220/1220 | 100% | ✓ fully populated |
| `tone` | 1220/1220 | 100% | ✓ |
| `transitions_per_second` | 1220/1220 | 100% | ✓ |
| `scene_count` | 1220/1220 | 100% | ✓ |
| `text_overlay_count` | 1220/1220 | 100% | ✓ |
| `analysis_json` (non-empty) | 1220/1220 | 100% | ✓ |
| `content_format` | 1196/1220 | 98% | 24 rows null; of populated, **37.4% = "other"** |
| `sound_id` | 1196/1220 | 98% | ✓ |
| `save_rate` | 1196/1220 | 98% | ✓ |
| `face_appears_at` | 965/1220 | **79%** | ~21% of videos silently missed the face-detect step |
| `cta_type` | 365/1220 | **30%** | Only 3-in-10 videos have a CTA classification |
| `breakout_multiplier` | 0/1220 | **0%** | **Column exists, schema-reserved, never written.** Dead signal. |

### The `hook_effectiveness` aggregate table is empty

Separately from per-video fields, Pattern + Ideas reports query a
niche-level aggregate table `hook_effectiveness` (computed per `niche_id
× hook_type`). Verified via live DB:

```
SELECT COUNT(*) FROM public.hook_effectiveness
→ 0
```

**No code path writes to it** in production. The only writer is
`supabase/seed.sql` (dev seed, never runs in prod). Three readers exist:

- `report_pattern_compute.py:411` — `load_pattern_inputs()`
- `report_ideas_compute.py:312` — `load_ideas_inputs()`
- `corpus_context.py:663` — claim-tier gate

Empty `hook_effectiveness` → `rank_hooks_for_pattern([])` returns `[]` →
`compute_positive_findings([])` returns `[]` → **Pattern + Ideas reports
render with zero hook findings, not a slower fallback**. There is no
`_derive_hook_patterns_from_corpus()` function in the codebase.

This is the single biggest reason Pattern + Ideas reports feel thin —
we own every signal needed to compute the aggregate (raw corpus has
play_count, digg_count, collect_count, hook_type on 1,220 videos), but
the computation never runs. See [Appendix B · Gap 1](#gap-1--hook_effectiveness-empty-in-prod--confirmed-worse).

### `content_format` distribution — the bucket quality

The 15-value taxonomy is a regex classifier that falls through to
`"other"` when none of the patterns match. Distribution today:

| content_format | n | % |
|---|---|---|
| **other** (catch-all) | **456** | **37.4%** |
| mukbang | 236 | 19.3% |
| tutorial | 136 | 11.1% |
| recipe | 116 | 9.5% |
| faceless | 81 | 6.6% |
| review | 55 | 4.5% |
| haul | 43 | 3.5% |
| _(null)_ | 24 | 2.0% |
| before_after | 15 | 1.2% |
| grwm | 15 | 1.2% |
| vlog | 12 | 1.0% |
| dance | 9 | 0.7% |
| storytelling | 9 | 0.7% |
| outfit_transition | 8 | 0.7% |
| comparison | 5 | 0.4% |

**The catch-all is the largest bucket.** Every downstream report
(pattern leaderboards, format lifecycle, timing-calendar kind
rotation) is reading against a taxonomy where **~2 of every 5 videos
are unclassifiable**. The 5 smallest buckets have ≤15 rows each
across the entire corpus — not enough to make per-format statements.

### `hook_type` distribution — healthier but concentrated

| hook_type | n | % |
|---|---|---|
| bold_claim | 281 | 23.0% |
| story_open | 190 | 15.6% |
| curiosity_gap | 182 | 14.9% |
| other | 132 | 10.8% |
| how_to | 131 | 10.7% |
| question | 107 | 8.8% |
| pain_point | 79 | 6.5% |
| social_proof | 43 | 3.5% |
| none | 30 | 2.5% |
| challenge | 22 | 1.8% |
| trend_hijack | 13 | 1.1% |
| controversy | 5 | 0.4% |
| shock_stat | 5 | 0.4% |

Healthier than content_format — top 3 buckets = 53.5%, "other" =
10.8%. But still: `controversy` + `shock_stat` at 5 each aren't
statistically usable.

### Gap to exceptional

| Target | Reason |
|---|---|
| **`content_format` "other" ≤ 10%** | Catch-all should be the exception, not the top bucket. Requires either better regex OR a Gemini-flash-lite reclassification pass for the "other" tail. |
| **`cta_type` coverage ≥ 80%** | 30% today means 70% of videos have no CTA signal. Either the detector is too strict or many videos genuinely lack a CTA — we don't know because there's no ground truth. |
| **`face_appears_at` coverage ≥ 95%** | 79% today. The 21% gap suggests silent extraction failures (Gemini rate-limit, first-frame grab failing) that should be surfaced in Axis 5. |
| **`breakout_multiplier` populated or removed** | A reserved schema column with 0 writes is dead infra. Either compute it (views vs niche median at ingest + refresh) or drop the column. |
| **`hook_effectiveness` table populated weekly** | Currently 0 rows → Pattern + Ideas reports have empty hook findings. Highest-leverage gap on this axis. |
| **Per-signal confidence scores** | Every classifier output should carry a confidence. Today: none stored. This is the prerequisite for Axis 4. |

### What it takes to close

1. **Build `hook_effectiveness_compute.py`** — batch job that groups
   `video_corpus` by (niche_id, hook_type), computes `avg_views`,
   `avg_engagement_rate`, `avg_save_rate`, `sample_size`, and
   `trend_direction` (current 30d vs prior 30d), and upserts on
   `(niche_id, hook_type)`. Wire into `/batch/analytics` as a final pass
   so one scheduled run populates everything. **This unlocks every
   existing Pattern + Ideas report** — no schema changes, no new UI.
2. **Reclassification pass for `content_format = 'other'`** — run
   Gemini Flash-Lite (~$0.002/video × 456 videos = ~$0.90) against the
   "other" tail with an expanded taxonomy prompt. This was evaluated
   and deferred in `corpus_ingest.classify_format` per the module
   docstring. Revisit the decision.
3. **Add confidence columns** — `hook_type_confidence`,
   `content_format_confidence` as numeric(3,2). Backfill nulls, start
   writing on new ingests. Unblocks Axis 4.
4. **Compute `breakout_multiplier` at ingest time** — views vs
   niche_median_30d. Re-compute on refresh (when Axis 3 lands).
5. **Investigate `face_appears_at` 21% miss rate** — is it Gemini
   failing, or is the extraction code inconsistent? Add a
   `has_face_analysis` boolean to distinguish "no face" from
   "extraction failed".

### SQL used

```sql
-- Field population counts
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE content_format IS NOT NULL)      AS has_content_format,
  COUNT(*) FILTER (WHERE content_format = 'other')        AS content_format_other,
  COUNT(*) FILTER (WHERE hook_type IS NOT NULL)           AS has_hook_type,
  COUNT(*) FILTER (WHERE cta_type IS NOT NULL)            AS has_cta_type,
  COUNT(*) FILTER (WHERE face_appears_at IS NOT NULL)     AS has_face,
  COUNT(*) FILTER (WHERE breakout_multiplier IS NOT NULL) AS has_breakout
FROM public.video_corpus;

-- Content-format histogram
SELECT content_format, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM public.video_corpus GROUP BY content_format ORDER BY n DESC;
```

---

## Axis 3 — Freshness / refresh discipline

### Current state

**Ingestion lag** (posted → indexed): **average 5 days.** That's fine
— we're catching content within a week of posting.

**Corpus recency:**

| Posted window | Count | % of corpus |
|---|---|---|
| ≤ 7 days | 502 | 42% |
| ≤ 30 days | 1,140 | 95% |
| ≤ 90 days | 1,196 | 100% |
| > 180 days | 0 | 0% |

Corpus is genuinely current. Not a chronological backfill of 2023
content — this is active TikTok output.

**Important caveat surfaced by the verification pass:** the freshness
we see is **manual-effort-bound, not scheduled.** `SELECT jobname FROM
cron.job` returns 4 jobs in production, all operational (expiry, free-
query reset, stuck-processing reset, webhook prune). **None schedule
`corpus_ingest` or `/batch/analytics`.** Someone grew the corpus from
0 to 1,220 videos over the last 12 days by running ingest by hand
via `deploy.sh` or a direct Cloud Run batch invocation. If that person
stops running it tomorrow, the corpus stops growing and ages into
staleness within weeks. See [Appendix B · Gap 4](#gap-4--no-weekly-cron-for-data-quality-jobs--confirmed-worse).

**BUT:** on top of the missing cron, the `video_corpus` schema also
has only one timestamp column: `indexed_at`. There is no `updated_at`,
no `last_refetched_at`, no evidence of re-ingestion. Views, likes,
comments, shares, engagement rate — **all frozen at ingest time.**

Concretely: if a video ingested on day 1 with 50K views went viral
to 5M views by day 7, our row still says 50K. Every downstream scoring
(breakout detection, timing-window lift multiplier, pattern
leaderboards) runs against day-1 numbers.

This is the specific mechanism by which the asset *decays* over time
even without losing rows: stale metrics, compounded by the absence of
both a refresh path AND a reliable ingest schedule.

### Gap to exceptional

| Target | Reason |
|---|---|
| **Top-quartile videos per niche refetched weekly** | A breakout is only visible with current numbers. Refetching the top quartile (≈10 videos × 21 niches = 210/week) captures the tail that actually moves. |
| **`last_refetched_at` column + backfill cron** | Schema change + cron. Straightforward. |
| **`views_at_ingest` column preserved** | When we overwrite `views`, we lose the ingest-time value. Preserve it separately so velocity (`views_now / views_at_ingest`) becomes a direct column. |
| **Per-niche refresh SLA: ≤ 7 days** | Matching the weekly cadence our reports already assume. |

### What it takes to close

1. **One migration** adds `last_refetched_at`, `views_at_ingest`
   columns. Backfill `views_at_ingest = views` for existing rows (loses
   history but future-proof).
2. **One Supabase Edge cron function** (`cron-refresh-corpus`) picks
   top-N videos per niche by `views`, calls EnsembleData to refetch
   metadata, updates the row. Reuse existing `ensemble.py` helpers.
3. **Surface refresh lag in observability** (Axis 5) — "oldest
   never-refreshed row per niche" as a health metric.

Est. 1-2 days of work including tests.

### SQL used

```sql
-- Schema evidence: indexed_at is the only ingest timestamp; no updated_at
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='video_corpus'
  AND (column_name LIKE '%_at' OR column_name LIKE 'updated%');

-- Ingest lag distribution
SELECT
  AVG(EXTRACT(EPOCH FROM (indexed_at - posted_at))/86400)::int AS avg_ingest_delay_days,
  COUNT(*) FILTER (WHERE posted_at > NOW() - INTERVAL '7 days')  AS posted_7d,
  COUNT(*) FILTER (WHERE posted_at > NOW() - INTERVAL '30 days') AS posted_30d,
  COUNT(*) FILTER (WHERE posted_at > NOW() - INTERVAL '90 days') AS posted_90d
FROM public.video_corpus;
```

---

## Axis 4 — Signal quality measurability

### Current state

**Nothing exists.** This is the shortest and most honest section in the
report.

Verification performed:

```
$ find . -type d \( -name "eval" -o -name "evals" -o -name "golden" \
      -o -name "ground_truth" -o -name "benchmarks" \) 2>/dev/null
  (no results)

$ grep -rln "golden_set\|ground_truth\|classifier_accuracy\|
             confusion_matrix\|eval_harness\|labeled_sample" cloud-run/ src/
  (no results)

$ grep -n "confidence" cloud-run/getviews_pipeline/corpus_ingest.py
  (no results)
```

What this means in practice:

- No hand-labeled Vietnamese video set against which our classifiers
  are scored. Every `hook_type = "bold_claim"` classification is
  asserted with zero audit.
- No confidence column on any classifier output. The extractor's
  certainty is discarded.
- No commit-over-commit regression. If someone changes the regex in
  `classify_format` tomorrow, we have no way of knowing whether it
  improved or regressed accuracy.
- No per-niche accuracy breakdown. A classifier that's 95% accurate
  on Skincare and 40% on Bất động sản is indistinguishable from one
  that's 70% on both.

### Gap to exceptional

| Target | Reason |
|---|---|
| **300–500-video hand-labeled Vietnamese golden set** | Stratified across all 21 niches, 20–30 videos each. Labels: `content_format`, `hook_type`, `cta_type`, `tone`, `face_appears_at_actual`. |
| **Eval harness that scores each classifier against the golden set** | CI-style: runs on every pipeline change, reports per-classifier precision/recall + per-niche accuracy breakdown. |
| **Confidence scores stored** (prerequisite from Axis 2) | Without these, we can't do threshold tuning. |
| **Regression-test budget: no deploy if any classifier drops >2pp** | CI gate, not aspirational. |

### What it takes to close

1. **Label the golden set.** 300 videos × ~2 min/label = 10 hours of
   focused Vietnamese-fluent labeling. Could be split across a week.
2. **Build the eval harness.** Read labeled CSV, run each classifier
   on the video's extracted features, score. ~1 day of code.
3. **Wire into CI.** Block deploys on >2pp regression. ~0.5 day.
4. **Publish a classifier scorecard** in `artifacts/docs/classifier-
   accuracy.md`, updated on each golden-set expansion.

**Total:** ~2-3 days, mostly the labeling.

**The ROI argument:** once the golden set exists, every future
classifier change becomes safe. Today a regex tweak is a blind
change. With the harness, we can confidently swap regex → Gemini
Flash-Lite (for the `content_format = 'other'` tail in Axis 2)
because we'll see immediately if accuracy moves.

---

## Axis 5 — Pipeline observability

### Current state

**The data pipeline has no schedule.** Before the health-signal
tables, this is the finding that reframes the axis. `cron.job` on the
live DB has exactly 4 rows:

| Job | Schedule | Purpose |
|---|---|---|
| `cron-expiry-check` | `0 2 * * *` | paid-pack expiry |
| `cron-reset-free-queries` | `0 17 * * *` | free-tier credit refill |
| `cron-reset-processing` | `*/5 * * * *` | stuck-state reset |
| `cron-prune-webhooks` | `0 20 * * 0` | webhook events GC |

**All operational. Zero touch the corpus.** No ingest cron, no
`/batch/analytics`, no `/batch/layer0`, no `hook_effectiveness`
recompute. "Observability" as originally framed assumed a pipeline
running that we needed to watch. The verification pass changes the
picture: **the pipeline itself doesn't run on a schedule**, and
that's the root gap. See [Appendix B · Gap 4](#gap-4--no-weekly-cron-for-data-quality-jobs--confirmed-worse).

Consequence visible elsewhere in this audit:

- **`hook_effectiveness` has 0 rows** (Axis 2) — nobody ever ran the
  compute.
- **`niche_insights` has 11 rows, `week_of = 2026-04-13`** (9+ days
  stale) — a one-off manual `/batch/layer0` invocation, never
  re-run. The video-diagnosis flow reads this table and now serves
  stale Layer-0 insights. See [Appendix B · Gap 2](#gap-2--niche_insights-disconnected-from-answer-reports--partially-correct).
- **Corpus growth** (Axis 1) happens by hand, not by cron.

### Health-signal tables (once a pipeline exists to observe)

| Table | Rows | Last write | Status |
|---|---|---|---|
| `video_corpus` | 1,220 | 2026-04-22 11:45 | ✓ active (manual trigger) |
| `gemini_calls` | 389 | 2026-04-22 15:00 | ✓ active (7d rolling: all 389 rows) |
| `ensemble_calls` | 453 | 2026-04-22 03:43 | ✓ active |
| `hook_effectiveness` | **0** | (never) | **Dead.** No writer. See Axis 2. |
| `niche_insights` | 11 | 2026-04-13 | Stale (9+ days, one manual run) |
| `batch_failures` | **0** | (never) | **Dead. Schema exists, 0 code paths write to it.** |
| `processed_webhook_events` | 0 | (never) | Idle (no PayOS traffic yet) |

**Gemini cost breakdown (rolling 7 days):**

```
total_calls:           389
total_usd:             $1.22
avg_usd_per_call:      $0.0031
avg_latency_ms:        43,107   ← 43 seconds average!
distinct_call_sites:   3
distinct_models:       2
```

**The 43s average latency is the first thing that should be
alerting** — it's consistent with Gemini vision on full-video ingest,
but we should know per call-site, not just an average.

**Schema gap:** `gemini_calls` has no `success` / `error_code` /
`retry_count` columns. We log that a call happened + what it cost +
how long it took, but not whether it succeeded. Silent failures
don't show up here. They show up as `analysis_json IS NULL` in
`video_corpus` (which we saw in Axis 2: 21% missing `face_appears_at`
is almost certainly silent Gemini failures).

### Gap to exceptional

| Target | Reason |
|---|---|
| **Data pipeline actually scheduled** | Before anything else: `/batch/analytics` (and ingest) need a `cron.schedule` row. Without a scheduled trigger there's nothing to observe. |
| **`batch_failures` actually written to** from ingest pipeline | Today the table is dead. Every silent failure should land here with a reason code. |
| **`gemini_calls.success` + `error_code` + `retry_count` columns** | Required to compute failure rate. |
| **Daily health digest (email or Slack)** | One row per day: videos ingested, rejection rate, niches below SLA, Gemini cost, Gemini failure rate, outlier latencies. |
| **Per-call-site latency SLO** | 43s is fine for vision-ingest; <2s for classifier pass; <5s for narrative synthesis. Track p50/p95 per call_site. |
| **Aggregation views** | `niche_health`, `pipeline_health_daily` SQL views that the digest reads. |

### What it takes to close

0. **Schedule the data pipeline first.** One `cron.schedule(...)` call
   pointed at `/batch/analytics` (extend the endpoint to run ingest
   → analytics → hook_effectiveness → layer0 in sequence). Until this
   row exists, every other item on this axis is watching an empty
   stream.
1. **Schema migration**: add `success`, `error_code`, `retry_count`
   to `gemini_calls` and `ensemble_calls`. Backfill `success = true`
   for existing rows (best guess).
2. **Ingest pipeline audit**: find every silent failure path (try/
   except that logs + swallows) and write a `batch_failures` row.
3. **SQL views**: `niche_health_daily`, `pipeline_health_daily`,
   `classifier_drift_weekly`.
4. **Supabase Edge cron** (`cron-daily-health-digest`) that reads the
   views, formats a digest, fires via Resend to an ops email.

Est. 2 days of work.

---

## Recommended order of operations

The verification pass (Appendix B) changes the original sequencing.
Before observability can be built we need *something on a schedule
that can be observed*. And before coverage growth matters we need
the aggregates that turn raw rows into usable signal. Revised order:

1. **Unblock the reports with `hook_effectiveness`** (Axis 2).
   **~1 day.** Build `hook_effectiveness_compute.py`, wire into
   `/batch/analytics` as a final pass. Populates the aggregate every
   Pattern + Ideas report queries — which is currently 0 rows and
   responsible for the most visible quality gap (empty hook findings
   on those reports). Highest leverage for least effort.
2. **Schedule the data pipeline** (Axis 5 Step 0). **~0.5 day.**
   One `cron.schedule` row pointing at `/batch/analytics`, extended
   to run ingest → analytics → hook_effectiveness → layer0 in sequence.
   Until this exists, the Gap 1 fix still depends on a human remembering
   to run the batch. This is where "data pipeline" actually starts to
   mean something.
3. **Observability instrumentation** (Axis 5). **~2 days.** Schema
   migration for `gemini_calls.success`, real writes to
   `batch_failures`, daily health digest. Now the cron from step 2
   has something watching it.
4. **Freshness / refresh cron** (Axis 3). **~1-2 days.**
   `last_refetched_at` column + weekly top-quartile refetch. Makes
   breakout detection run on current numbers instead of ingest-time
   numbers.
5. **Wire `niche_insights` into Answer reports** (Appendix B · Gap 2).
   **~0.5 day.** Add a fetcher in `report_pattern_compute` +
   `report_ideas_compute`, inject `insight_text` + `execution_tip`
   into the narrative prompts. Uses real schema columns, not the
   proposal's hallucinated ones.
6. **Depth improvements** (Axis 2 tail). Variable.
   `content_format = 'other'` reclassification pass, `cta_type` 70%
   investigation, `breakout_multiplier` computation, confidence
   columns.
7. **Quality measurability / eval harness** (Axis 4). ~2-3 days
   including golden-set labeling (~10h Vietnamese-fluent). Now safe
   classifier changes, commit-over-commit.
8. **Coverage growth** (Axis 1). Variable — ingest throughput
   bottleneck will now be measurable (cron runs are observable
   after steps 2-3). Grow from 1,220 → target (≥20K rolling 30d).

**Total estimate to reach "exceptional" on all 5:** ~2 weeks of
focused work, excluding the golden-set labeling which is a
separate track.

**What to NOT do:** do not start observability instrumentation
(step 3) before a data-pipeline cron exists (step 2). Instrumenting
an empty stream produces no signal. The original sequence ("Axis 5
first") was wrong because it assumed the pipeline was running —
it isn't.

---

## Appendix — Marketing copy discrepancy

Grep-caught during this audit: the landing page
(`src/routes/_index/LandingPage.tsx`) and login screen
(`src/routes/_auth/login/route.tsx`) both claim:

> "Data thực từ 46.000+ video TikTok Việt Nam"

Actual corpus size today: **1,220 videos**. Off by a factor of ~37×.

This is orthogonal to the quality-discipline argument but should be
flagged for legal/trust hygiene. Two resolutions:

- **Ship Axis 1** (corpus growth) to reality-match the claim, OR
- **Update the copy** to a range the data actually supports today
  (e.g. "1.200+ video Vietnamese creators phân tích từng khung
  hình" — focuses on depth rather than breadth).

The second is cheap and immediate. The first is a moat-investment
decision.

---

## Appendix B — Pipeline gap verification (2026-04-22)

Verified against live DB + codebase against a separate proposal of "4 core
pipeline gaps." Each gap re-checked from scratch. Findings below update
the Axis severity ranking above — two gaps are **worse than described**,
one is **partially correct** with schema errors, one is **already fixed**.

### Gap 1 — `hook_effectiveness` empty in prod · **CONFIRMED (worse)**

**Evidence:**
- Live DB query: `SELECT COUNT(*) FROM hook_effectiveness` → **0 rows**.
- Readers exist at 3 call sites (Pattern + Ideas + corpus_context claim-tier gate).
- Only writer is `supabase/seed.sql:270` — dev-only seed, never runs in prod.
- No batch job, no cron, no code path writes this table.

**Claim correction:** The proposal mentioned a
`_derive_hook_patterns_from_corpus()` fallback. That function **does not
exist.** When `hook_effectiveness` returns `[]`, `rank_hooks_for_pattern([])`
returns `[]`, `compute_positive_findings([])` returns `[]`, and the Pattern
report renders with **zero hook findings**. Same for Ideas. This isn't a
performance bug (it's not "silently falling through to a slow path"); it's
a correctness bug — **reports render with missing data, not slower data**.

**Cross-reference to Axis 2:** this is the single biggest reason Pattern +
Ideas reports feel thin. Our own 1,220 videos carry every signal we need to
compute `hook_effectiveness` rows on — we just don't.

### Gap 2 — `niche_insights` disconnected from Answer reports · **PARTIALLY CORRECT**

**Evidence:**
- Live DB: `niche_insights` has **11 rows**, 1 per niche, latest `week_of = 2026-04-13` (9 days stale).
- Reader exists at `pipelines.py:_get_niche_insight()` (line 1012), called from `pipelines.py:1238` in the **video_diagnosis** flow.
- **No Answer-session report module** (pattern/ideas/timing/lifecycle/diagnostic/generic) reads it.

**Schema correction — the proposal references columns that don't exist:**

| Proposal column | Schema actual | |
|---|---|---|
| `week_start` | **`week_of`** | wrong name |
| `common_hook_mechanism` | — | does not exist |
| `retention_driver` | — | does not exist |
| `common_timing` | — | does not exist |
| `common_visual` | — | does not exist |

The actual schema has: `insight_text, mechanisms, cross_niche_signals, execution_tip, staleness_risk, quality_flag, top_formula_hook, top_formula_format`.

**The real work:** wire `insight_text` + `execution_tip` into `fill_pattern_narrative` + `fill_ideas_narrative` (those are the populated fields). The four non-existent columns in the proposal need to be dropped from any fetch query or this fix won't compile.

### Gap 3 — Fixture confidence strip misleads users · **ALREADY FIXED**

**Evidence:**
- `report_lifecycle.py` line 557-560 (from commit `2ca28d1`, merged 2026-05-07):
  ```python
  if cells_are_fixture:
      conf["sample_size"] = 0
      conf["intent_confidence"] = "low"
  ```
- Additionally, commit `41bbfb8` (merged same day) **rerouted** `fatigue` + `subniche_breakdown` intents off `answer:lifecycle` onto `answer:pattern` entirely — new sessions don't even hit the fixture path.

Gap 3 is closed. No action needed.

### Gap 4 — No weekly cron for data-quality jobs · **CONFIRMED (worse)**

**Evidence:** `SELECT jobname FROM cron.job` on live DB returns exactly 4 jobs, all **operational** (payment + session lifecycle), none touching the data pipeline:

| Job | Schedule | Purpose |
|---|---|---|
| `cron-expiry-check` | `0 2 * * *` | paid-pack expiry |
| `cron-reset-free-queries` | `0 17 * * *` | free-tier credit refill |
| `cron-reset-processing` | `*/5 * * * *` | `profiles.is_processing` stuck-state reset |
| `cron-prune-webhooks` | `0 20 * * 0` | `processed_webhook_events` GC |

**Claim correction:** The proposal stated "existing pg_cron schedules call `/batch/analytics` and `/batch/layer0`." **They do not.** Neither endpoint is scheduled. Both exist in `cloud-run/getviews_pipeline/routers/batch.py` but can only be invoked manually.

**The actual data-pipeline cron surface is empty.** This is why:
- `niche_insights` has 11 rows from `week_of 2026-04-13`, 9+ days stale — a one-off manual `/batch/layer0` run.
- `hook_effectiveness` has 0 rows — nobody ever called the (hypothetical) compute.
- Corpus ingest lives outside pg_cron entirely — whoever grew the corpus from 0 to 1,220 over the last 12 days did it via `deploy.sh` or direct Cloud Run batch invocation.

This compounds every finding above. **Axis 5 (observability) and Axis 3 (freshness) findings in the main body understate the problem by assuming crons exist but aren't surfacing failures. In reality, the crons don't exist.**

### Updated severity ranking

| Axis | Before Appendix B | After Appendix B |
|---|---|---|
| 1. Coverage | Small corpus, enforcement gap | Same + coverage grew by hand, not by cron |
| 2. Depth | Coarse classifiers, dead columns | **+hook_effectiveness empty → reports missing hook data** |
| 3. Freshness | No refresh path | **+ freshness only holds because someone ran ingest by hand** |
| 4. Quality | No eval harness | unchanged |
| 5. Observability | Dead `batch_failures` | **+ no data-pipeline crons at all, only operational ones** |

### Revised order of operations

Original (main body) order still stands — Axis 5 first — but **Gap 1 + Gap 4 are the wedge.** Before any observability instrumentation makes sense, we need *something running on a schedule that can be observed*.

Suggested first concrete PR, ~1 day:

1. Write `hook_effectiveness_compute.py` (per the proposal, adapted to real schema).
2. Wire into existing `/batch/analytics` endpoint as Pass 4 (one request does everything).
3. **Schedule `/batch/analytics` itself as a weekly pg_cron job** — right now it's documentation-only in migration `20260410000015`.
4. Observe the first cron run + surface success/failure via the `batch_failures` table (separately: add the write path).

That gives us: populated `hook_effectiveness`, weekly refresh, and the first real data-pipeline cron actually running. Axis 5 observability instrumentation lands on top of a pipeline that *exists*, rather than observing nothing.
