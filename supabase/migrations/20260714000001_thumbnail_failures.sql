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

-- No RLS policies are defined — no direct client reads or writes allowed.
-- INSERT: Edge Function uses service_role key (bypasses RLS).
-- SELECT: admin panel uses SECURITY DEFINER RPCs below (bypass RLS at the
--         function level). Direct table queries from user JWTs are always denied.
-- Dashboard access: Supabase dashboard uses service_role and bypasses RLS natively.

-- RPC: total failure count in a time window.
-- SECURITY DEFINER runs as the function owner (service_role equivalent) — bypasses RLS.
-- set search_path guards against search_path injection attacks.
CREATE OR REPLACE FUNCTION thumbnail_failures_count_7d(cutoff_ts TIMESTAMPTZ)
RETURNS BIGINT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COUNT(*)
  FROM thumbnail_failures
  WHERE failed_at >= cutoff_ts;
$$;

-- RPC: top-10 most-failed video_ids in a time window.
-- SECURITY DEFINER runs as the function owner — bypasses RLS.
CREATE OR REPLACE FUNCTION thumbnail_failures_top10(cutoff_ts TIMESTAMPTZ)
RETURNS TABLE(video_id TEXT, count BIGINT)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public
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
