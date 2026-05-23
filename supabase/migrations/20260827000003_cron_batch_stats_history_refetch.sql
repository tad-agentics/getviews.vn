-- §4.7 M4 — hourly stats_history refetch (T+6h / T+24h) via batch pod.
--
-- Runs every hour UTC; ``/batch/stats-history-refetch`` selects rows whose
-- ``first_seen_at`` crossed the 6h or 24h window and appends ED snapshots.
--
-- Rollback:
--   SELECT cron.unschedule('cron-batch-stats-history-refetch');

SELECT cron.schedule(
  'cron-batch-stats-history-refetch',
  '15 * * * *',
  $cmd$
  SELECT net.http_post(
    url := (
      SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url'
    ) || '/batch/stats-history-refetch?limit=80',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (
        SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret'
      )
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 600000
  );
  $cmd$
);
