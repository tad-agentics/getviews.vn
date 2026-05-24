-- HI-13 throughput — split nightly corpus ingest into 3 pg_cron shifts (class loop).
--
-- With Gemini Batch API, a single /batch/ingest run cannot cover ~43 active
-- content_class_ingest_targets within the 3600s Cloud Run cap. Each shift gets
-- a full wall_clock_budget_s (~3400s) and one third of classes by priority.
--
-- Schedules (UTC → ICT +7):
--   cron-batch-ingest           0 20 * * *  → 03:00  shift a
--   cron-batch-ingest-shift-b  30 21 * * *  → 04:30  shift b
--   cron-batch-ingest-shift-c   0 23 * * *  → 06:00  shift c (MV refresh when complete)
--
-- cron-batch-post-processing (30 23 UTC) still heals MV if shift c aborts.
--
-- Verify:
--   SELECT jobname, schedule, command FROM cron.job
--   WHERE jobname LIKE 'cron-batch-ingest%';

SELECT cron.alter_job(
  j.jobid,
  j.schedule,
  $cmd$
SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/ingest',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{"ingest_shift":"a","ingest_shift_count":3}'::jsonb,
    timeout_milliseconds := 3540000
  );
$cmd$
)
FROM cron.job j
WHERE j.jobname = 'cron-batch-ingest';

SELECT cron.schedule(
  'cron-batch-ingest-shift-b',
  '30 21 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/ingest',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{"ingest_shift":"b","ingest_shift_count":3}'::jsonb,
    timeout_milliseconds := 3540000
  );
  $cmd$
);

SELECT cron.schedule(
  'cron-batch-ingest-shift-c',
  '0 23 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/ingest',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{"ingest_shift":"c","ingest_shift_count":3}'::jsonb,
    timeout_milliseconds := 3540000
  );
  $cmd$
);
