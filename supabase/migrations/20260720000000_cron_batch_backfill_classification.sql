-- ME-17 — Daily legacy-row classification backfill (text-only Gemini over analysis_json).
--
-- Schedule: 04:00 UTC (after nightly ingest window; see pipeline plan).
-- Target: POST /batch/backfill-classification on the **batch** Cloud Run URL
--         (vault ``cloud_run_api_url`` must point at the service that mounts ``/batch/*``).

SELECT cron.schedule(
  'cron-backfill-classification',
  '0 4 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/backfill-classification',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{"batch_size":3500,"max_runtime_s":3300,"dry_run":false}'::jsonb,
    timeout_milliseconds := 2700000
  );
  $cmd$
);

-- Unschedule:
--   SELECT cron.unschedule('cron-backfill-classification');
