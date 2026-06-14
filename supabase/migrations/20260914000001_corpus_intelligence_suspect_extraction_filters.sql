-- Recreate benchmark MVs: exclude boost-suspect from base (views/ER hygiene);
-- structural aggregates skip degraded extraction only (keep sample_size for min-sample gate).

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS content_class_intelligence CASCADE;

CREATE MATERIALIZED VIEW content_class_intelligence AS
WITH base AS (
  SELECT
    content_class_id, hook_type, tone, views, engagement_rate, face_appears_at,
    transitions_per_second, video_duration, text_overlay_count, is_commerce,
    dialect, cta_type, has_vietnamese_hashtags, has_caption_text, hashtag_count,
    is_original_sound, scene_count, extraction_quality
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
    AND COALESCE(boost_attribution, '') NOT IN ('suspect_low', 'suspect_medium')
),
win_7d AS (
  SELECT
    content_class_id,
    COUNT(*)::integer AS video_count_7d,
    AVG(views)::double precision AS avg_views_7d
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '7 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
    AND COALESCE(boost_attribution, '') NOT IN ('suspect_low', 'suspect_medium')
  GROUP BY content_class_id
),
win_prior_7d AS (
  SELECT
    content_class_id,
    COUNT(*)::integer AS video_count_prior_7d,
    AVG(views)::double precision AS avg_views_prior_7d
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '14 days'
    AND indexed_at <= NOW() - interval '7 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
    AND COALESCE(boost_attribution, '') NOT IN ('suspect_low', 'suspect_medium')
  GROUP BY content_class_id
),
velocity AS (
  SELECT
    COALESCE(w.content_class_id, p.content_class_id) AS content_class_id,
    w.video_count_7d,
    p.video_count_prior_7d,
    w.avg_views_7d,
    p.avg_views_prior_7d,
    w.avg_views_7d / NULLIF(p.avg_views_prior_7d, 0) AS view_velocity,
    w.video_count_7d::double precision / NULLIF(p.video_count_prior_7d, 0) AS format_momentum
  FROM win_7d w
  FULL OUTER JOIN win_prior_7d p ON p.content_class_id = w.content_class_id
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
struct_ok AS (
  SELECT * FROM base
  WHERE COALESCE(extraction_quality, 'ok') <> 'degraded'
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
    (SELECT AVG(s.face_appears_at) FILTER (WHERE s.face_appears_at IS NOT NULL) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS avg_face_appears_at,
    (SELECT COUNT(*) FILTER (WHERE s.face_appears_at IS NOT NULL AND s.face_appears_at <= 0.5) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE s.face_appears_at IS NOT NULL), 0) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS pct_face_in_half_sec,
    (SELECT AVG(s.transitions_per_second) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS avg_transitions_per_second,
    (SELECT AVG(s.video_duration) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS avg_duration,
    (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.video_duration) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS median_duration,
    (SELECT MIN(s.video_duration) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS min_duration,
    (SELECT MAX(s.video_duration) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS max_duration,
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
    (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.scene_count) FROM struct_ok s WHERE s.content_class_id = b.content_class_id) AS median_scene_count
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
  v.video_count_7d,
  v.video_count_prior_7d,
  v.avg_views_7d,
  v.avg_views_prior_7d,
  v.view_velocity,
  v.format_momentum,
  CASE
    WHEN COALESCE(v.video_count_7d, 0) < 5 THEN NULL
    WHEN a.sample_size < 10 THEN NULL
    WHEN v.avg_views_prior_7d IS NULL OR v.avg_views_prior_7d = 0
      OR v.video_count_prior_7d IS NULL OR v.video_count_prior_7d = 0
      THEN 'new_class'
    WHEN v.format_momentum > 1.5 THEN 'emerging'
    WHEN v.format_momentum > 1.1 THEN 'growing'
    WHEN v.format_momentum < 0.8 THEN 'declining'
    ELSE 'peak'
  END AS lifecycle_stage,
  NOW() AS computed_at
FROM agg a
LEFT JOIN hook_dist h ON h.content_class_id = a.content_class_id
LEFT JOIN tone_dist t ON t.content_class_id = a.content_class_id
LEFT JOIN velocity v ON v.content_class_id = a.content_class_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_intelligence_pk
  ON content_class_intelligence(content_class_id);

GRANT SELECT ON content_class_intelligence TO authenticated;

COMMENT ON MATERIALIZED VIEW content_class_intelligence IS
  'Class cohort stats; base excludes boost-suspect; structural fields exclude degraded extraction.';

-- Tier MV: suspect filter on base only (views/ER aggregates).
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
    AND COALESCE(boost_attribution, '') NOT IN ('suspect_low', 'suspect_medium')
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
