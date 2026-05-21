-- Content-class corpus pivot — Phase 4: browse MV claim_tier, class channel benchmarks, optional niche sunset.

BEGIN;

-- Extend content_class_intelligence with browse claim tier (Phase 1 parity).
DROP MATERIALIZED VIEW IF EXISTS content_class_intelligence CASCADE;

CREATE MATERIALIZED VIEW content_class_intelligence AS
WITH base AS (
  SELECT * FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
),
hook_dist AS (
  SELECT content_class_id, jsonb_object_agg(hook_type, cnt) AS hook_distribution
  FROM (
    SELECT content_class_id, hook_type, COUNT(*) AS cnt
    FROM base WHERE hook_type IS NOT NULL
    GROUP BY content_class_id, hook_type
  ) x
  GROUP BY content_class_id
),
tone_dist AS (
  SELECT content_class_id, jsonb_object_agg(tone, cnt) AS tone_distribution
  FROM (
    SELECT content_class_id, tone, COUNT(*) AS cnt
    FROM base WHERE tone IS NOT NULL
    GROUP BY content_class_id, tone
  ) x
  GROUP BY content_class_id
),
agg AS (
  SELECT
    b.content_class_id,
    COUNT(*) AS sample_size,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS p50_views,
    AVG(b.views) AS avg_views,
    AVG(b.engagement_rate) AS avg_engagement_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
    AVG(b.face_appears_at) FILTER (WHERE b.face_appears_at IS NOT NULL) AS avg_face_appears_at,
    COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL AND b.face_appears_at <= 0.5) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL), 0) AS pct_face_in_half_sec,
    AVG(b.transitions_per_second) AS avg_transitions_per_second,
    AVG(b.video_duration) AS avg_duration,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.video_duration) AS median_duration,
    MIN(b.video_duration) AS min_duration,
    MAX(b.video_duration) AS max_duration,
    AVG(b.text_overlay_count) AS avg_text_overlays,
    COUNT(*) FILTER (WHERE b.is_commerce) * 100.0 / NULLIF(COUNT(*), 0) AS commerce_pct,
    AVG(b.views) FILTER (WHERE b.is_commerce) AS commerce_avg_views,
    AVG(b.views) FILTER (WHERE NOT b.is_commerce) AS organic_avg_views,
    COUNT(*) FILTER (WHERE b.dialect = 'southern') AS southern_count,
    COUNT(*) FILTER (WHERE b.dialect = 'northern') AS northern_count,
    COUNT(*) FILTER (WHERE b.cta_type IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) AS has_cta_pct,
    COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags IS NOT NULL), 0) AS pct_has_specific_hashtags,
    COUNT(*) FILTER (WHERE b.has_caption_text = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.has_caption_text IS NOT NULL), 0) AS pct_has_caption_text,
    AVG(b.hashtag_count) AS avg_hashtag_count,
    COUNT(*) FILTER (WHERE b.is_original_sound = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.is_original_sound IS NOT NULL), 0) AS pct_original_sound,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.scene_count) AS median_scene_count
  FROM base b
  GROUP BY b.content_class_id
)
SELECT
  a.content_class_id,
  a.sample_size,
  COALESCE(h.hook_distribution, '{}'::jsonb) AS hook_distribution,
  COALESCE(t.tone_distribution, '{}'::jsonb) AS tone_distribution,
  a.avg_face_appears_at,
  a.pct_face_in_half_sec,
  a.avg_transitions_per_second,
  a.avg_duration,
  a.median_duration,
  a.min_duration,
  a.max_duration,
  a.avg_engagement_rate,
  a.median_er,
  a.median_views,
  a.p50_views,
  a.avg_views,
  a.avg_text_overlays,
  a.commerce_pct,
  a.commerce_avg_views,
  a.organic_avg_views,
  a.southern_count,
  a.northern_count,
  a.has_cta_pct,
  a.pct_has_specific_hashtags,
  a.pct_has_caption_text,
  a.avg_hashtag_count,
  a.pct_original_sound,
  a.median_scene_count,
  CASE
    WHEN a.sample_size >= 50 THEN 'strong'
    WHEN a.sample_size >= 30 THEN 'moderate'
    WHEN a.sample_size >= 10 THEN 'early'
    ELSE 'thin'
  END AS claim_tier,
  NOW() AS computed_at
FROM agg a
LEFT JOIN hook_dist h ON h.content_class_id = a.content_class_id
LEFT JOIN tone_dist t ON t.content_class_id = a.content_class_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_intelligence_pk
  ON content_class_intelligence(content_class_id);

GRANT SELECT ON content_class_intelligence TO authenticated;

CREATE OR REPLACE FUNCTION refresh_content_class_intelligence()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY content_class_intelligence;
END;
$$;

REVOKE EXECUTE ON FUNCTION refresh_content_class_intelligence() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION refresh_content_class_intelligence() FROM anon;
REVOKE EXECUTE ON FUNCTION refresh_content_class_intelligence() FROM authenticated;
GRANT EXECUTE ON FUNCTION refresh_content_class_intelligence() TO service_role;

-- Junction aggregate for pill thin-claim (optional RPC).
CREATE OR REPLACE FUNCTION content_class_stats_for_creator_niche(p_creator_niche_id integer)
RETURNS TABLE (
  content_class_id integer,
  sample_size bigint,
  claim_tier text
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT cci.content_class_id, cci.sample_size::bigint, cci.claim_tier
  FROM creator_niche_content_classes j
  JOIN content_class_intelligence cci ON cci.content_class_id = j.content_class_id
  WHERE j.creator_niche_id = p_creator_niche_id;
$$;

GRANT EXECUTE ON FUNCTION content_class_stats_for_creator_niche(integer) TO authenticated, anon, service_role;

-- Class + tier channel benchmarks (replaces niche_channel_benchmarks for score card when class known).
CREATE OR REPLACE FUNCTION content_class_channel_benchmarks(
  p_content_class_id integer,
  p_creator_tier text DEFAULT NULL
)
RETURNS TABLE (
  channel_count integer,
  avg_views_p50 integer,
  avg_views_p75 integer,
  engagement_p50 numeric,
  engagement_p75 numeric,
  posts_per_week_p50 numeric,
  posts_per_week_p75 numeric
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  WITH per_creator AS (
    SELECT
      creator_handle,
      AVG(views)::float AS avg_views,
      AVG(engagement_rate)::float AS avg_er,
      (COUNT(*)::float
         / GREATEST(
             EXTRACT(EPOCH FROM (MAX(posted_at) - MIN(posted_at))) / 604800.0,
             1.0
           )) AS posts_per_week
    FROM video_corpus
    WHERE content_class_id = p_content_class_id
      AND indexed_at > NOW() - interval '30 days'
      AND views > 0
      AND (p_creator_tier IS NULL OR creator_tier = p_creator_tier)
    GROUP BY creator_handle
    HAVING COUNT(*) >= 3
  )
  SELECT
    COUNT(*)::integer AS channel_count,
    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_views), 0)::integer AS avg_views_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_views), 0)::integer AS avg_views_p75,
    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_er), 0)::numeric AS engagement_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_er), 0)::numeric AS engagement_p75,
    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric AS posts_per_week_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric AS posts_per_week_p75
  FROM per_creator;
$$;

GRANT EXECUTE ON FUNCTION content_class_channel_benchmarks(integer, text) TO authenticated, anon, service_role;

COMMENT ON FUNCTION content_class_channel_benchmarks(integer, text) IS
  'Phase 4 — channel score card percentiles scoped to content_class (+ optional creator_tier peer band).';

COMMIT;
