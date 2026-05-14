-- Rename ``count`` column in ``thumbnail_failures_top10`` RETURNS TABLE
-- to ``fail_count`` to avoid the reserved-word foot-gun. PostgREST + the
-- FE both happen to deserialise the lowercase ``count`` field fine,
-- but ``count`` clashes with the SQL function name and JS reserved-word
-- conventions in some clients. Renaming pre-empts future churn.
--
-- Also DROP + RECREATE the function because Postgres can't alter the
-- RETURNS TABLE signature via CREATE OR REPLACE.

DROP FUNCTION IF EXISTS thumbnail_failures_top10(TIMESTAMPTZ);

CREATE FUNCTION thumbnail_failures_top10(cutoff_ts TIMESTAMPTZ)
RETURNS TABLE(video_id TEXT, fail_count BIGINT)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    video_id,
    COUNT(*) AS fail_count
  FROM thumbnail_failures
  WHERE failed_at >= cutoff_ts
  GROUP BY video_id
  ORDER BY fail_count DESC
  LIMIT 10;
$$;
