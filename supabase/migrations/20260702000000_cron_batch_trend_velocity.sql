-- Sound Radar (L2.2 Sprint 2) — schedule the standalone trend_velocity runner.
--
-- ``/batch/trend-velocity`` reads the Monday-aligned ``trending_sounds``
-- table to compute weekly sound deltas (accelerating / peaking /
-- cooling buckets) and writes them into the ``sound_trends`` JSONB
-- column on ``trend_velocity``. The pattern report's L1.4
-- ``top_sounds`` cell then renders ↑/→/↓ icons next to each sound
-- name on the FE.
--
-- Runs Mondays 22:30 UTC = 30 min after ``cron-batch-sound-aggregate``
-- (Monday 21:30 UTC) so trending_sounds.week_of for the just-started
-- week is already fresh when the delta computation reads it.
--
-- Pre-launch corpus is ~5k videos / 18 niches. Per-niche compute is
-- pure SQL aggregation, so the full job runs in seconds — no risk of
-- pg_cron's 300s timeout firing.

SELECT cron.schedule(
  'cron-batch-trend-velocity',
  '30 22 * * 1',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/trend-velocity',
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
--   SELECT cron.unschedule('cron-batch-trend-velocity');
