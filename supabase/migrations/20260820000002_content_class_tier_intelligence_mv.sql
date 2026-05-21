-- Phase 2 — peer-band MV: (content_class_id, creator_tier) aggregates.

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS content_class_tier_intelligence CASCADE;

CREATE MATERIALIZED VIEW content_class_tier_intelligence AS
WITH base AS (
  SELECT *
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
    AND creator_tier IS NOT NULL
)
SELECT
  b.content_class_id,
  b.creator_tier,
  COUNT(*) AS sample_size,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY b.views) AS p75_views,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
  AVG(b.views) AS avg_views,
  AVG(b.engagement_rate) AS avg_engagement_rate,
  NOW() AS computed_at
FROM base b
GROUP BY b.content_class_id, b.creator_tier;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_tier_intelligence_pk
  ON content_class_tier_intelligence (content_class_id, creator_tier);

GRANT SELECT ON content_class_tier_intelligence TO authenticated;

CREATE OR REPLACE FUNCTION refresh_content_class_tier_intelligence()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY content_class_tier_intelligence;
END;
$$;

REVOKE EXECUTE ON FUNCTION refresh_content_class_tier_intelligence() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION refresh_content_class_tier_intelligence() FROM anon;
REVOKE EXECUTE ON FUNCTION refresh_content_class_tier_intelligence() FROM authenticated;
GRANT EXECUTE ON FUNCTION refresh_content_class_tier_intelligence() TO service_role;

COMMIT;
