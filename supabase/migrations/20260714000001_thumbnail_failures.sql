-- thumbnail_failures — observability table for frontend thumbnail load errors.
--
-- Populated via the `track-thumbnail-failure` Edge Function called from
-- VideoThumbnail.tsx's onError handler (via navigator.sendBeacon).
-- De-duplicated client-side per video_id per session; this table may still
-- receive low-volume duplicates across sessions but that is acceptable.
--
-- Access:
--   INSERT: Edge Function (service_role via anon key passthrough) — RLS allows
--           no direct client writes. The edge function validates Origin before writing.
--   SELECT: Admin only — not exposed to end users.
--
-- Retention: no automatic TTL. Prune manually or add a cron once volume is known.
-- Expected volume: O(100s) per week — bulk purge via:
--   DELETE FROM thumbnail_failures WHERE failed_at < NOW() - INTERVAL '90 days';

CREATE TABLE thumbnail_failures (
  id         BIGSERIAL PRIMARY KEY,
  video_id   TEXT        NOT NULL,
  failed_url TEXT,
  user_agent TEXT,
  failed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX thumbnail_failures_failed_at_idx ON thumbnail_failures (failed_at DESC);
CREATE INDEX thumbnail_failures_video_id_idx  ON thumbnail_failures (video_id);

ALTER TABLE thumbnail_failures ENABLE ROW LEVEL SECURITY;

-- No direct client reads or writes allowed.
-- The Edge Function inserts using the service_role key.
-- Admin queries bypass RLS via service_role on the Supabase dashboard.

-- RPC for the admin panel: top-10 most-failed video_ids in a time window.
-- Called with service_role from the admin hook — no auth policy needed here
-- because the panel bypasses RLS via the service_role client.
CREATE OR REPLACE FUNCTION thumbnail_failures_top10(cutoff_ts TIMESTAMPTZ)
RETURNS TABLE(video_id TEXT, count BIGINT)
LANGUAGE SQL
SECURITY DEFINER
AS $$
  SELECT
    video_id,
    COUNT(*) AS count
  FROM thumbnail_failures
  WHERE failed_at >= cutoff_ts
  GROUP BY video_id
  ORDER BY count DESC
  LIMIT 10;
$$;
