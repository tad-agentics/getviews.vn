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
| **1. Coverage** | 1,220 videos across 21 niches. Max 128, median ~50, min 6. | Every niche is below the 500-video "exceptional" floor. Top-of-funnel is a bottleneck. Landing-page marketing copy claims "46.000+ videos" — **off by 37×.** |
| **2. Analysis depth** | 100% of rows have hook_type + tone + scene_count. But 37% of rows bucket to `content_format = 'other'` (classifier catch-all) and only 30% have `cta_type`. The `breakout_multiplier` column is populated on **0 of 1,220 rows**. | The classifiers are coarse (regex) and one declared signal is entirely dead. Vietnamese-specific depth is shallower than the schema suggests. |
| **3. Freshness** | Corpus is 12 days old total (oldest indexed 2026-04-10). No `updated_at` column. Views/likes/engagement stamped once at ingest and never refreshed. | Trend detection runs on stale view counts. A video that went viral post-ingest is invisible to our scoring. |
| **4. Quality measurability** | **Zero golden set. Zero eval harness.** No accuracy tracking. No confidence scores stored per classification. No commit-over-commit regression testing on classifier output. | We can't answer "did this pipeline change make the data better or worse?" |
| **5. Observability** | `batch_failures` table exists, has 0 rows, and **no code path writes to it.** No `success` column on `gemini_calls`. No cron for ingest (runs manually). No daily-health digest. | Silent failure surface is huge. We'd only notice an ingestion outage by eyeballing `video_corpus` counts. |

**The meta-finding:** we've built a pipeline but we haven't built a
**quality discipline around the pipeline**. The discipline is what a
data company has and a SaaS app doesn't. Closing that gap is the moat.

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
| **Per-signal confidence scores** | Every classifier output should carry a confidence. Today: none stored. This is the prerequisite for Axis 4. |

### What it takes to close

1. **Reclassification pass for `content_format = 'other'`** — run
   Gemini Flash-Lite (~$0.002/video × 456 videos = ~$0.90) against the
   "other" tail with an expanded taxonomy prompt. This was evaluated
   and deferred in `corpus_ingest.classify_format` per the module
   docstring. Revisit the decision.
2. **Add confidence columns** — `hook_type_confidence`,
   `content_format_confidence` as numeric(3,2). Backfill nulls, start
   writing on new ingests. Unblocks Axis 4.
3. **Compute `breakout_multiplier` at ingest time** — views vs
   niche_median_30d. Re-compute on refresh (when Axis 3 lands).
4. **Investigate `face_appears_at` 21% miss rate** — is it Gemini
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

**BUT:** the `video_corpus` schema has one timestamp column:
`indexed_at`. There is no `updated_at`, no `last_refetched_at`, no
evidence of re-ingestion. Views, likes, comments, shares, engagement
rate — **all frozen at ingest time.**

Concretely: if a video ingested on day 1 with 50K views went viral
to 5M views by day 7, our row still says 50K. Every downstream scoring
(breakout detection, timing-window lift multiplier, pattern
leaderboards) runs against day-1 numbers.

This is the specific mechanism by which the asset *decays* over time
even without losing rows: stale metrics.

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

**Health-signal tables exist but most are dead or non-aggregated.**

| Table | Rows | Last write | Status |
|---|---|---|---|
| `video_corpus` | 1,220 | 2026-04-22 11:45 | ✓ active |
| `gemini_calls` | 389 | 2026-04-22 15:00 | ✓ active (7d rolling: all 389 rows) |
| `ensemble_calls` | 453 | 2026-04-22 03:43 | ✓ active |
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
| **`batch_failures` actually written to** from ingest pipeline | Today the table is dead. Every silent failure should land here with a reason code. |
| **`gemini_calls.success` + `error_code` + `retry_count` columns** | Required to compute failure rate. |
| **Daily health digest (email or Slack)** | One row per day: videos ingested, rejection rate, niches below SLA, Gemini cost, Gemini failure rate, outlier latencies. |
| **Per-call-site latency SLO** | 43s is fine for vision-ingest; <2s for classifier pass; <5s for narrative synthesis. Track p50/p95 per call_site. |
| **Aggregation views** | `niche_health`, `pipeline_health_daily` SQL views that the digest reads. |

### What it takes to close

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

If the goal is to build "visual intelligence data company" quality
discipline, the five axes sequence naturally:

1. **Axis 5 first (observability).** ~2 days. You can't fix what you
   can't see. Dead `batch_failures` table + no Gemini success column
   means every Axis 1–4 improvement lands in a black box. Fixing
   observability makes every subsequent improvement measurable.
2. **Axis 3 (freshness).** ~1-2 days. Add `last_refetched_at` column
   + refresh cron. Small schema change, immediate user impact on
   breakout detection accuracy.
3. **Axis 2 (analysis depth).** Variable. The `breakout_multiplier`
   computation lands with Axis 3 naturally. The `content_format = 'other'`
   tail reclassification is ~0.5 day + $1 in Gemini. The `cta_type`
   70% gap needs investigation first.
4. **Axis 4 (quality measurability).** ~2-3 days. Most of the cost is
   the labeling exercise. Once the harness exists, every future
   classifier change becomes safe to ship.
5. **Axis 1 (coverage).** Variable — depends on ingestion-speed
   bottleneck which we haven't measured yet. Axis 5's observability
   will expose whether it's EnsembleData rate-limit, Gemini
   throughput, or batch-schedule frequency.

**Total estimate to reach "exceptional" on all 5:** ~2 weeks of
focused work, excluding the golden-set labeling which is a
separate track.

**What to NOT do:** do not start any of this without first landing
observability (Axis 5). Without the observability layer, everything
else is blind work.

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
