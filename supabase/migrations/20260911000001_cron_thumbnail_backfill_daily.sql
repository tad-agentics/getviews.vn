-- Reference tiles fix (2026-06-11): thumbnail backfill weekly → DAILY.
--
-- The 500-row cap per run (20260910000000_cron_thumbnail_backfill_limit500)
-- is correct for the 3600s Cloud Run timeout, but at WEEKLY cadence the
-- remaining ~2.7K legacy NULL rows take 5+ weeks to drain — and analysis
-- reference tiles ("VIDEO THAM CHIẾU") kept rendering gray placeholders
-- because reference selection draws from that cohort. Daily at the same
-- cap drains the backlog in ~6 days and thereafter heals any new phantom
-- within 24h. Still scheduled after the Sunday R2 janitor window.

SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname = 'cron-batch-backfill-thumbnails';

SELECT cron.schedule(
  'cron-batch-backfill-thumbnails',
  '0 19 * * *',
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

UPDATE public.expected_cron_jobs
SET note = 'daily 19:00 — thumbnail self-heal, 500 rows/run (NULLs + phantom R2)'
WHERE jobname = 'cron-batch-backfill-thumbnails';
