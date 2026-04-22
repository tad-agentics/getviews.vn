-- 2026-05-09 — pg_cron schedule for /batch/refresh (corpus freshness).
--
-- Addendum to ``20260509000001_pg_cron_data_pipeline.sql``. Adds the
-- daily metadata refresh cron that calls /batch/refresh — re-pulls
-- views/likes/comments/shares/saves from EnsembleData for the
-- top-priority video_corpus rows. Closes the Axis 3 freshness gap.
--
-- The DDL is commented like its siblings — apply via Dashboard once
-- the Vault secrets are seeded (cloud_run_api_url, cloud_run_batch_secret).
--
-- Why daily: cost is ~$0.10/run for 200 rows, and breakouts that
-- happen post-ingest get caught within ~24h instead of waiting on the
-- weekly analytics cron. Why 22:30 UTC: 30 min after the daily
-- /batch/ingest at 20:00 UTC + 30 min after analytics finishes (when
-- it runs Sundays). That keeps the pipeline ordering: ingest new →
-- refresh existing → aggregate → emit insights.

-- SELECT cron.schedule(
--   'cron-batch-refresh',
--   '30 22 * * *',                 -- daily 22:30 UTC = 05:30 Vietnam
--   $cmd$
--   SELECT net.http_post(
--     url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/refresh',
--     headers := jsonb_build_object(
--       'Content-Type', 'application/json',
--       'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
--     ),
--     body := '{}'::jsonb,
--     timeout_milliseconds := 180000  -- 3 min; ED post-multi is fast
--   );
--   $cmd$
-- );

-- Rollback:
--   SELECT cron.unschedule('cron-batch-refresh');

SELECT 1;
