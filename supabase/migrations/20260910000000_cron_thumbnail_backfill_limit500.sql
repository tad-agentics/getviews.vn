-- Cap weekly thumbnail backfill at 500 rows per run so Cloud Run's 3600s
-- request ceiling is not hit (full-corpus run on 2026-06-10 timed out at 504
-- after ~1,751 heals with ~6,000 rows still pending). Idempotent re-schedule.

SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname = 'cron-batch-backfill-thumbnails';

SELECT cron.schedule(
  'cron-batch-backfill-thumbnails',
  '0 19 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url')
      || '/batch/backfill-thumbnails?ed_fallback=true&limit=500',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 3540000
  );
  $cmd$
);
