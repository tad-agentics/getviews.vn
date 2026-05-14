-- channel_diagnoses cleanup cron — enforce the documented 7-day TTL.
--
-- Migration 20260715000000_channel_diagnoses_table.sql comments
-- ``7-day TTL enforced by application layer'' but the BE only uses
-- the cutoff as a read filter (_fetch_channel_diagnoses_cache:283
-- ``.gte("computed_at", cutoff)``). Rows older than 7 days are
-- ignored on read but never deleted — the table grows unbounded
-- (~one row per (handle, video_url, niche_id) tuple per request,
-- pre-launch low volume but post-launch will accumulate fast).
--
-- This cron deletes rows older than 14 days (one read-TTL window
-- of safety on top of the 7-day freshness gate). Runs daily at
-- 02:15 UTC — lowest user-traffic window for VN (09:15 ICT, off
-- peak before morning ritual cron at 15:00 UTC / 22:00 ICT).
--
-- Rollback:
--   SELECT cron.unschedule('cron-channel-diagnoses-prune');

SELECT cron.schedule(
  'cron-channel-diagnoses-prune',
  '15 2 * * *',
  $cmd$
  DELETE FROM public.channel_diagnoses
   WHERE computed_at < now() - interval '14 days';
  $cmd$
);
