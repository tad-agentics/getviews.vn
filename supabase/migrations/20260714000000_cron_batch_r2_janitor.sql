-- R2 Janitor weekly cron — reconcile Cloudflare R2 storage against video_corpus.
--
-- When a ``video_corpus`` row is deleted (niche rotation, dedup, manual cleanup),
-- its R2 objects (frames/, thumbnails/, videos/, video_shots/) are NOT automatically
-- removed — they live outside the DB transaction boundary. This cron calls
-- POST /batch/r2-janitor on the batch pod weekly to delete orphaned objects.
--
-- The janitor:
--   - Pulls the live video_id set from video_corpus into memory once per run.
--   - Streams R2 objects in 1000-key pages per prefix and reconciles.
--   - Deletes in batches of up to 1000 (S3 DeleteObjects cap).
--   - Defaults to dry_run=true; this schedule passes dry_run=false (destructive).
--   - Cost: ~$0.20 per full sweep (R2 LIST + DELETE class A ops at corpus scale).
--
-- Schedule: Sundays 18:00 UTC = 01:00 ICT Monday — low user traffic window.
-- timeout_milliseconds: 600000 (10 min) — full corpus sweep is well under 10 min.
--
-- Pre-launch validation: run `POST /batch/r2-janitor?dry_run=true` manually first
-- and eyeball per-prefix orphan counts before applying this migration. If counts
-- look unexpected (e.g. all videos/ flagged orphan), it indicates a key-pattern
-- drift in r2.py — fix the pattern before running destructive.
--
-- Rollback:
--   SELECT cron.unschedule('cron-batch-r2-janitor');

SELECT cron.schedule(
  'cron-batch-r2-janitor',
  '0 18 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url') || '/batch/r2-janitor?dry_run=false',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 600000
  );
  $cmd$
);
