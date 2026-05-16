-- CR-2 — Raise pg_net HTTP timeout for cron-batch-ingest (pipeline audit)
--
-- net.http_post(..., timeout_milliseconds := 300000) cuts the outbound
-- request at 5 minutes while Python /batch/ingest is budgeted for ~50 minutes
-- wall-clock. pg_cron continues; pg_net abandons the HTTP wait first.
--
-- Alters the existing named job in place (schedule preserved). If the job is
-- absent (fresh local DB), this SELECT affects 0 rows and is a no-op.
--
-- Verify on production after apply:
--   SELECT jobname, schedule, command FROM cron.job WHERE jobname = 'cron-batch-ingest';
--   -- command must contain: timeout_milliseconds := 3120000  (52 minutes)
--
-- Note: cron.alter_job() updates the job command only; the timeout is the
-- pg_net client parameter inside that command, not a pg_cron max_runtime knob.

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
    timeout_milliseconds := 3120000
  );
$cmd$
)
FROM cron.job j
WHERE j.jobname = 'cron-batch-ingest';
