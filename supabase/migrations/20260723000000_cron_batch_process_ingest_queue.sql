-- Daily drain of corpus_ingest_queue → full Gemini reingest on batch pod.
--
-- Schedule: 01:30 UTC daily (~08:30 ICT) — after cron-batch-post-processing
-- (23:30 UTC) and usual /batch/ingest window (20:00 UTC), so the batch pod
-- is unlikely to be busy with the nightly wave.
--
-- Uses same Vault secrets as other /batch/* crons (cloud_run_api_url MUST
-- point at the batch service — see TD note in system-design).
--
-- Rollback:
--   SELECT cron.unschedule('cron-batch-process-ingest-queue');

SELECT cron.schedule(
  'cron-batch-process-ingest-queue',
  '30 1 * * *',
  $cmd$
  SELECT net.http_post(
    url := (
      SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url'
    ) || '/batch/process-ingest-queue?limit=50',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (
        SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret'
      )
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 3600000
  );
  $cmd$
);
