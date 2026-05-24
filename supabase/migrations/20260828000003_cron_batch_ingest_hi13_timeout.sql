-- HI-13 ingest tuning — raise pg_net HTTP timeout to match 3400s wall-clock budget.
--
-- After enabling Gemini Batch API, a single BATCH_CONCURRENCY wave can block ~40+ min
-- on slow batch polls. Default wall_clock_budget_s is now 3400s (was 3000s).
-- pg_net must outlive the Cloud Run request (3600s cap).
--
-- Verify: SELECT command FROM cron.job WHERE jobname = 'cron-batch-ingest';
--   → timeout_milliseconds := 3540000  (59 min)

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
    body := '{}'::jsonb,
    timeout_milliseconds := 3540000
  );
$cmd$
)
FROM cron.job j
WHERE j.jobname = 'cron-batch-ingest';
