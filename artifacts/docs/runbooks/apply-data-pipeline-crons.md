# Runbook — Apply the data-pipeline crons

**Status:** ready to execute
**Last verified:** 2026-05-09
**Owner:** ops (one-time setup)
**Expected duration:** ~10 minutes (plus ~5 minutes waiting for smoke-test cron fire)
**Reversibility:** fully reversible — rollback section at the bottom

---

## Purpose

Three PRs shipped in May 2026 put the data-pipeline infrastructure in
place, but none of it is running yet because no cron is scheduled to
fire the `/batch/*` endpoints:

| Shipped | What it does | Why it's dormant |
|---|---|---|
| `hook_effectiveness_compute.py` (#109) | Populates the `hook_effectiveness` aggregate every week | Never called — table still has 0 rows |
| `corpus_refresh.py` (#114) | Daily refresh of `video_corpus` view counts for top-priority rows | Never called |
| `batch_observability.py` (#113) | Records one row per `/batch/*` run in `batch_job_runs` | Writes correctly when called; just nothing is calling |

This runbook applies the four `cron.schedule()` calls proposed in
`supabase/migrations/20260509000001_pg_cron_data_pipeline.sql` and
`20260509000004_pg_cron_corpus_refresh.sql` (both docs-only). Once
applied, the pipeline runs on its own.

---

## Pre-flight

Run these **before touching anything**. If any check fails, stop and
investigate — do not proceed.

```sql
-- 1. Extensions are installed.
SELECT extname, extversion FROM pg_extension
 WHERE extname IN ('pg_cron', 'pg_net')
 ORDER BY extname;
-- Expect: pg_cron@1.6.4 (or later), pg_net@0.20.0 (or later).

-- 2. Schema migrations are applied.
SELECT
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_name = 'batch_job_runs' AND table_schema = 'public') AS batch_job_runs_exists,
  EXISTS (SELECT 1 FROM information_schema.columns
          WHERE table_name = 'video_corpus' AND column_name = 'last_refetched_at' AND table_schema = 'public') AS last_refetched_at_exists,
  EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hook_effectiveness_niche_hook_unique') AS hook_unique_exists;
-- Expect: all three true.

-- 3. No data-pipeline crons already exist (should be fresh install).
SELECT jobname FROM cron.job
 WHERE jobname LIKE 'cron-batch-%';
-- Expect: 0 rows. If any row returns, see "Rollback" and decide.
```

---

## Step 1 — Gather the two secrets

You need two values before running any SQL:

### 1a. Cloud Run batch secret

The value of `BATCH_SECRET` in the Cloud Run service's env vars. Used
as the `X-Batch-Secret` header by the cron HTTP POST.

```bash
# Read from the live service.
gcloud run services describe getviews-pipeline \
  --region asia-southeast1 \
  --format='value(spec.template.spec.containers[0].env)' \
  | grep -oP 'BATCH_SECRET[^,]+'
```

If `BATCH_SECRET` is not set on the Cloud Run service, pick a strong
random value (`openssl rand -hex 32`) and set it on both sides:

```bash
gcloud run services update getviews-pipeline \
  --region asia-southeast1 \
  --update-env-vars BATCH_SECRET=<hex-value>
```

### 1b. Cloud Run API base URL

```bash
gcloud run services describe getviews-pipeline \
  --region asia-southeast1 \
  --format='value(status.url)'
# Example: https://getviews-pipeline-aabbccdd-as.a.run.app
```

Save both values. Do **not** commit them anywhere.

---

## Step 2 — Seed Vault

Run this in the Supabase SQL editor (the Dashboard) as the `postgres`
role, NOT via PostgREST / MCP. Vault writes go through the `vault`
schema and need the elevated session.

```sql
SELECT vault.create_secret(
  '<value from step 1a>',
  'cloud_run_batch_secret',
  'Shared secret for X-Batch-Secret header on /batch/* endpoints'
);

SELECT vault.create_secret(
  '<value from step 1b>',        -- no trailing slash
  'cloud_run_api_url',
  'Base URL for the Cloud Run pipeline service'
);
```

Verify:

```sql
SELECT name, description, created_at
FROM vault.secrets
WHERE name IN ('cloud_run_batch_secret', 'cloud_run_api_url')
ORDER BY name;
-- Expect: two rows.

-- Optional — confirm decryption round-trips.
SELECT name, LEFT(decrypted_secret, 20) AS preview
FROM vault.decrypted_secrets
WHERE name IN ('cloud_run_batch_secret', 'cloud_run_api_url')
ORDER BY name;
```

---

## Step 3 — Manual smoke test (critical — do not skip)

**Before scheduling a cron, fire the endpoint once by hand.** If it
fails, we fix it once and move on. If we skip this step and schedule a
broken cron, the next pg_cron fire will write a failure to
`batch_job_runs` and we get paged instead.

```bash
# Takes ~60 seconds. Will populate hook_effectiveness with real rows
# and land a batch_job_runs entry.
curl -X POST \
  -H "X-Batch-Secret: <value from step 1a>" \
  -H "Content-Type: application/json" \
  -d '{}' \
  https://<value from step 1b>/batch/analytics
```

Expected response (ok):

```json
{
  "ok": true,
  "analytics": { "creators_updated": <N>, "videos_updated": <N>, "errors": [] },
  "signal":    { "grades_written": <N>, "niches_processed": <N>, "errors": [] },
  "patterns":  { "rows_updated": <N> },
  "hook_effectiveness": {
    "upserted": <N>,           // expect ~50-70 based on 2026-04-22 smoke
    "current_buckets": <N>,
    "prior_buckets": <N>
  }
}
```

Verify the observability + aggregate writes landed:

```sql
-- One row in batch_job_runs, status='ok', summary populated.
SELECT id, job_name, status, duration_ms, summary->'hook_effectiveness'
FROM public.batch_job_runs
ORDER BY started_at DESC
LIMIT 1;

-- hook_effectiveness is no longer empty.
SELECT COUNT(*) AS n, MAX(computed_at) AS latest
FROM public.hook_effectiveness;
-- Expect: n > 0, latest = now-ish.
```

If `status = 'failed'` or `hook_effectiveness` is still 0, **stop**.
Check `summary->'error'` and Cloud Run logs. Do not proceed to cron.

---

## Step 4 — Apply the cron schedules

Copy-paste this whole block into the Supabase SQL editor in one
transaction. Running in one shot means either all four land or none do.

```sql
-- 4 data-pipeline crons. All use Vault secrets set in step 2.
-- UTC schedules — Vietnam is UTC+7.

-- Daily ingest at 20:00 UTC (03:00 Vietnam, before morning-ritual).
SELECT cron.schedule(
  'cron-batch-ingest',
  '0 20 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/ingest',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 300000
  );
  $cmd$
);

-- Daily refresh at 22:30 UTC (05:30 Vietnam, 30 min after ingest).
SELECT cron.schedule(
  'cron-batch-refresh',
  '30 22 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/refresh',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 180000
  );
  $cmd$
);

-- Weekly analytics Sun 21:00 UTC (Mon 04:00 Vietnam).
SELECT cron.schedule(
  'cron-batch-analytics',
  '0 21 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/analytics',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 300000
  );
  $cmd$
);

-- Weekly layer0 Sun 21:30 UTC (Mon 04:30 Vietnam, 30 min after analytics).
SELECT cron.schedule(
  'cron-batch-layer0',
  '30 21 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/layer0',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 600000
  );
  $cmd$
);
```

Verify all four landed:

```sql
SELECT jobid, jobname, schedule, active
FROM cron.job
WHERE jobname LIKE 'cron-batch-%'
ORDER BY jobid;
-- Expect: 4 rows, all active=true.
```

---

## Step 5 — Wait for first real cron fires + verify

The earliest upcoming fire depends on the current UTC time. Check:

```sql
-- What's the next-expected fire time for each?
-- pg_cron doesn't expose this directly but you can derive it by
-- inspecting the schedule + current time.
SELECT jobname, schedule
FROM cron.job
WHERE jobname LIKE 'cron-batch-%'
ORDER BY jobname;

-- After the first scheduled window passes, confirm the run logged:
SELECT runid, jobid, status, return_message,
       start_time, end_time
FROM cron.job_run_details
WHERE jobid IN (SELECT jobid FROM cron.job WHERE jobname LIKE 'cron-batch-%')
ORDER BY start_time DESC
LIMIT 10;
-- Expect: status='succeeded' per run.

-- And a matching row in batch_job_runs from the Cloud Run side:
SELECT job_name, status, duration_ms, summary
FROM public.batch_job_runs
WHERE job_name LIKE 'batch/%'
ORDER BY started_at DESC
LIMIT 10;
```

If a `cron.job_run_details` row shows `status='failed'`, the SQL call
itself failed (e.g. Vault lookup broken). If it shows succeeded but
the `batch_job_runs` side shows `status='failed'`, the Cloud Run body
raised — check the `error` column on that row for the exception + the
Cloud Run logs for the traceback.

---

## Rollback

To remove the data-pipeline crons (the operational ones stay
untouched):

```sql
SELECT cron.unschedule('cron-batch-ingest');
SELECT cron.unschedule('cron-batch-refresh');
SELECT cron.unschedule('cron-batch-analytics');
SELECT cron.unschedule('cron-batch-layer0');

-- Confirm removal.
SELECT jobname FROM cron.job WHERE jobname LIKE 'cron-batch-%';
-- Expect: 0 rows.
```

Vault secrets can stay — they're harmless without a cron referencing
them. If you also want those gone:

```sql
DELETE FROM vault.secrets
WHERE name IN ('cloud_run_batch_secret', 'cloud_run_api_url');
```

---

## Post-apply monitoring

Once the crons have been firing for a week, run this weekly-ish to
catch silent failures that don't alert loudly enough yet:

```sql
-- Last run per data-pipeline job + the count of failures in 7d.
WITH recent AS (
  SELECT
    job_name,
    MAX(started_at) AS last_run,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failures_7d,
    SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS successes_7d
  FROM public.batch_job_runs
  WHERE started_at > NOW() - INTERVAL '7 days'
  GROUP BY job_name
)
SELECT
  job_name,
  last_run,
  successes_7d,
  failures_7d,
  CASE WHEN failures_7d > 0 THEN 'INVESTIGATE' ELSE 'ok' END AS health
FROM recent
ORDER BY job_name;
```

If `failures_7d > 0`, inspect the failing row's `error` column and
the matching Cloud Run log window. The `stale-hook-effectiveness`
case to specifically watch: if `summary->'hook_effectiveness'->>'upserted'`
drops to 0 unexpectedly, the aggregate stopped updating and Pattern
+ Ideas reports are about to silently regress.

---

## Next actions after this lands

1. **Axis 5 follow-through:** add an `admin/alert_rules` entry that
   fires when `failures_7d > 0` on any `cron-batch-*` job. Today the
   `batch_job_runs` write surfaces the failure, but nothing reads it.
2. **Step 7 (corpus growth):** schedule remains daily, but the
   `/batch/ingest` endpoint's per-niche prioritisation logic should
   be upgraded to target thin niches first. See state-of-corpus
   Axis 1 gap "Per-niche backfill logic".
