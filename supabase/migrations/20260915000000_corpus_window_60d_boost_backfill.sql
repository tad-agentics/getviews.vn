-- Corpus window 60d: boost_attribution backfill on legacy unknown rows + recreate benchmark MVs.
-- Python defaults: CORPUS_BENCHMARK_WINDOW_DAYS=60, CORPUS_REFERENCE_*=60 (see corpus_windows.py).


-- Backfill boost_attribution on pre-classification rows (parity with classify_boost_suspect).
WITH stats AS (
  SELECT
    percentile_cont(0.10) WITHIN GROUP (
      ORDER BY (vc.comments::float / NULLIF(vc.views, 0))
    ) AS p10_comment_rate,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY vc.engagement_rate) AS p25_er,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY vc.views) AS p75_views,
    percentile_cont(0.90) WITHIN GROUP (ORDER BY vc.views) AS p90_views
  FROM video_corpus vc
  WHERE vc.content_type = 'video'
    AND vc.views > 0
    AND vc.language = 'vi'
    AND vc.indexed_at > NOW() - interval '60 days'
),
classified AS (
  SELECT
    vc.video_id,
    CASE
      WHEN (
        (
          vc.views >= s.p90_views
          AND (
            COALESCE(vc.engagement_rate, 0) < s.p25_er
            OR (vc.comments::float / NULLIF(vc.views, 0)) < s.p10_comment_rate
          )
        )
        OR (vc.comments = 0 AND vc.views >= GREATEST(s.p75_views, 10000))
      ) THEN 'suspect_medium'
      WHEN vc.views >= s.p90_views
        AND COALESCE(vc.engagement_rate, 0) < s.p25_er * 1.25
        THEN 'suspect_low'
      ELSE 'organic_confident'
    END AS new_boost
  FROM video_corpus vc
  CROSS JOIN stats s
  WHERE vc.content_type = 'video'
    AND vc.views > 0
    AND COALESCE(vc.boost_attribution, '') IN ('unknown', '')
)
UPDATE video_corpus vc
SET
  boost_attribution = c.new_boost,
  reference_eligible = (c.new_boost <> 'suspect_medium')
FROM classified c
WHERE vc.video_id = c.video_id;

-- Recreate benchmark MVs: exclude boost-suspect from base (views/ER hygiene);
-- structural aggregates skip degraded extraction only (keep sample_size for min-sample gate).
--
-- CASCADE on content_class_intelligence drops the dependent
-- creator_niche_content_class_stats MV (LEFT JOIN cci) — it is recreated below.
-- Grants mirror the post-advisor state (20260826000000): content_class_intelligence
-- keeps authenticated (read client-side by useTopNiches etc.), anon revoked; the
-- tier + creator_niche stats MVs are service_role-only (anon + authenticated revoked).

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
  WHERE indexed_at > NOW() - interval '60 days'
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
agg AS (
  -- ``_ok`` filters keep structural aggregates (scene/transition/duration/face)
  -- clean of degraded extractions, while sample_size / views / ER use every
  -- non-suspect row so thin classes stay above the 15-row benchmark gate.
  SELECT
    b.content_class_id,
    COUNT(*) AS sample_size,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS p50_views,
    AVG(b.views) AS avg_views,
    AVG(b.engagement_rate) AS avg_engagement_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
    AVG(b.face_appears_at) FILTER (
      WHERE b.face_appears_at IS NOT NULL AND COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS avg_face_appears_at,
    COUNT(*) FILTER (
      WHERE b.face_appears_at IS NOT NULL AND b.face_appears_at <= 0.5
        AND COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) * 100.0 / NULLIF(COUNT(*) FILTER (
      WHERE b.face_appears_at IS NOT NULL AND COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ), 0) AS pct_face_in_half_sec,
    AVG(b.transitions_per_second) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS avg_transitions_per_second,
    AVG(b.video_duration) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS avg_duration,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.video_duration) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS median_duration,
    MIN(b.video_duration) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS min_duration,
    MAX(b.video_duration) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS max_duration,
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
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.scene_count) FILTER (
      WHERE COALESCE(b.extraction_quality, 'ok') <> 'degraded'
    ) AS median_scene_count
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

-- Post-advisor grant state: authenticated keeps SELECT, anon revoked.
GRANT SELECT ON content_class_intelligence TO authenticated;
REVOKE SELECT ON content_class_intelligence FROM anon;

COMMENT ON MATERIALIZED VIEW content_class_intelligence IS
  'Class cohort stats (60d base); excludes boost-suspect; structural fields exclude degraded extraction.';

-- Recreate dependent dropped by CASCADE (def from 20260823000004); service_role-only grants.
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

REVOKE SELECT ON creator_niche_content_class_stats FROM anon, authenticated;

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

-- Tier MV: suspect filter on base only (views/ER aggregates). Service_role-only.
DROP MATERIALIZED VIEW IF EXISTS content_class_tier_intelligence CASCADE;

CREATE MATERIALIZED VIEW content_class_tier_intelligence AS
WITH base AS (
  SELECT *
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '60 days'
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

REVOKE SELECT ON content_class_tier_intelligence FROM anon, authenticated;

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
