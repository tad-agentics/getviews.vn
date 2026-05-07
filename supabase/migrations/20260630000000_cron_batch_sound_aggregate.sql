-- Schedule the L1.4 sound aggregator as a standalone weekly cron.
--
-- ``run_sound_aggregation`` previously only fired at the END of
-- ``/batch/ingest``. The full daily ingest occasionally exceeds the
-- pg_cron 5-minute HTTP timeout, killing the aggregator step before
-- ``trending_sounds`` gets refreshed. Symptom (verified in production
-- 2026-05-06): ``trending_sounds.MAX(week_of)`` stuck at 2026-04-27 for
-- a full week even though daily ingest kept landing video_corpus rows
-- with ``sound_id`` populated. The L1.4 pattern report's ``top_sounds``
-- cell silently degrades to last week's sounds.
--
-- Standalone aggregator (``POST /batch/sound-aggregate``) runs in ~30s
-- so this cron never trips the timeout. Schedule chosen to fire 30 min
-- after the weekly ``cron-batch-analytics`` so the corpus is settled
-- and any late-Sunday ingest writes are visible.
--
-- Schedule chosen: Mondays 21:30 UTC (= Tuesday 04:30 VN). One slot
-- after ``cron-batch-analytics`` (Sunday 21:00 UTC) and ``cron-batch-
-- layer0`` (Sunday 21:30 UTC). The aggregator's ``_week_start_monday``
-- helper rounds today() to Monday, so Tuesday's run writes the correct
-- ``week_of`` for the just-started week.

SELECT cron.schedule(
  'cron-batch-sound-aggregate',
  '30 21 * * 1',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/sound-aggregate',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 120000
  );
  $cmd$
);

-- Rollback:
--   SELECT cron.unschedule('cron-batch-sound-aggregate');
