-- ME-16 — Daily post-processing cron (MV refresh, Video Đáng Học, Layer 0B sound, Sunday weekly).
--
-- Runs after the main ingest window so aborted wall-clock ingests still heal
-- materialized views + downstream aggregates. Complements inline post-processing
-- at the end of a successful ``/batch/ingest``.
--
-- Schedule: 23:30 UTC daily.

SELECT cron.schedule(
  'cron-batch-post-processing',
  '30 23 * * *',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/post-processing',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 2700000
  );
  $cmd$
);
