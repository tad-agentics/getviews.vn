-- Missing-thumbnails root fix (audit 2026-06-10): the self-healing endpoint
-- POST /batch/backfill-thumbnails existed but was never scheduled — it only
-- ran by hand (last: 2026-05-25). Result in production on 2026-06-10:
-- 3,649/9,290 corpus rows (39%) with thumbnail_url IS NULL (Apr 20–May 18
-- ingest cohort, pre mirror-at-ingest) and 171 browser-reported failures/30d
-- on phantom R2 URLs (DB row points at R2, object missing).
--
-- The endpoint heals both classes per run: NULL rows retry frame[0] → CDN →
-- fresh EnsembleData cover, and every R2-prefixed row is HEAD-verified so
-- phantom URLs are reprocessed. Idempotent, safe to re-run.
--
-- Schedule: Sundays 19:00 UTC (02:00 ICT Monday) — right AFTER
-- cron-batch-r2-janitor (18:00 UTC Sunday) so anything the janitor removes
-- is re-mirrored the same night, and clear of the 20:00–23:30 ingest shifts.
--
-- Verify:
--   SELECT jobname, schedule FROM cron.job WHERE jobname = 'cron-batch-backfill-thumbnails';
--   -- after a run:
--   SELECT status_code FROM net._http_response ORDER BY id DESC LIMIT 5;

SELECT cron.schedule(
  'cron-batch-backfill-thumbnails',
  '0 19 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/backfill-thumbnails?ed_fallback=true',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 3540000
  );
  $cmd$
);
