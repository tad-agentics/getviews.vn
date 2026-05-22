-- Recreate creator_niche_content_class_stats dropped by CASCADE in 20260823000001
-- (content_class_intelligence MV recreate). Must run after 00001.

BEGIN;

CREATE MATERIALIZED VIEW creator_niche_content_class_stats AS
SELECT
  j.creator_niche_id,
  j.content_class_id,
  j.is_primary,
  COALESCE(cci.sample_size, 0)::integer AS sample_size,
  COALESCE(cci.claim_tier, 'thin') AS claim_tier,
  COALESCE(cci.avg_views, 0)::bigint AS avg_views,
  COALESCE(cci.median_er, 0)::numeric AS median_er,
  NOW() AS computed_at
FROM creator_niche_content_classes j
LEFT JOIN content_class_intelligence cci ON cci.content_class_id = j.content_class_id;

CREATE UNIQUE INDEX idx_creator_niche_cc_stats_pk
  ON creator_niche_content_class_stats(creator_niche_id, content_class_id);

CREATE INDEX idx_creator_niche_cc_stats_niche_sample
  ON creator_niche_content_class_stats(creator_niche_id, sample_size DESC);

GRANT SELECT ON creator_niche_content_class_stats TO authenticated;

CREATE OR REPLACE FUNCTION refresh_creator_niche_content_class_stats()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY creator_niche_content_class_stats;
END;
$$;

REVOKE EXECUTE ON FUNCTION refresh_creator_niche_content_class_stats() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION refresh_creator_niche_content_class_stats() FROM anon;
REVOKE EXECUTE ON FUNCTION refresh_creator_niche_content_class_stats() FROM authenticated;
GRANT EXECUTE ON FUNCTION refresh_creator_niche_content_class_stats() TO service_role;

COMMIT;
