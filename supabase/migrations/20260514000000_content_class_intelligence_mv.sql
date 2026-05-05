-- A.2.1 (two-axis deep pivot, 2026-05-14) — content_class_intelligence MV.
--
-- Parallel to ``niche_intelligence`` but keyed on
-- ``content_classifications.id`` instead of ``niche_taxonomy.id`` so
-- downstream analytics can compute benchmarks at the (topic × format)
-- granularity introduced in PR1 + PR2 of the two-axis refactor.
--
-- ── Why ─────────────────────────────────────────────────────────────
--
-- ``niche_intelligence`` aggregates 30 days of corpus per niche. With
-- the two-axis taxonomy we know each video is also tagged with a
-- ``content_class_id`` (e.g. food_recipe_tutorial vs food_restaurant_review).
-- These have different production conventions — recipe is top-down
-- camera + voice-over, restaurant review is POV vlog. Computing a
-- single niche-wide median blurs them and produces noisy benchmarks
-- like "average duration 35s" when in reality recipe is 90s and POV
-- review is 15s.
--
-- This MV gives us per-content_class aggregates so reports
-- (compute_pulse, pattern thesis, video diagnosis) can pivot to a
-- sharper baseline once A.2.3 plumbs the read paths through.
--
-- ── Sample size caveat ──────────────────────────────────────────────
--
-- Pre-launch corpus is small; many content_classes will have <30 rows
-- in a 30-day window. Consumers MUST gate on sample_size before
-- displaying claims (matches the existing ``claim_tiers`` discipline
-- in niche_intelligence land). The MV still emits rows for thin
-- buckets so the read layer can fall back to niche_intelligence
-- transparently.
--
-- ── Idempotency ─────────────────────────────────────────────────────
--
-- DROP IF EXISTS + CREATE — safe to re-run. Refresh function uses
-- CONCURRENTLY so callers don't block on long aggregations.

BEGIN;

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
)
SELECT
  b.content_class_id,
  COUNT(*) AS sample_size,
  COALESCE(h.hook_distribution, '{}'::jsonb) AS hook_distribution,
  -- format_distribution intentionally omitted: content_class already
  -- encodes format_axis (each content_class has one format). Including
  -- it would just produce { "<one_format>": <sample_size> } per row.
  COALESCE(t.tone_distribution, '{}'::jsonb) AS tone_distribution,

  AVG(b.face_appears_at) FILTER (WHERE b.face_appears_at IS NOT NULL) AS avg_face_appears_at,
  COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL AND b.face_appears_at <= 0.5) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL), 0) AS pct_face_in_half_sec,

  AVG(b.transitions_per_second) AS avg_transitions_per_second,
  AVG(b.video_duration) AS avg_duration,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.video_duration) AS median_duration,
  MIN(b.video_duration) AS min_duration,
  MAX(b.video_duration) AS max_duration,

  AVG(b.engagement_rate) AS avg_engagement_rate,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
  AVG(b.views) AS avg_views,

  AVG(b.text_overlay_count) AS avg_text_overlays,

  COUNT(*) FILTER (WHERE b.is_commerce) * 100.0 /
    NULLIF(COUNT(*), 0) AS commerce_pct,
  AVG(b.views) FILTER (WHERE b.is_commerce) AS commerce_avg_views,
  AVG(b.views) FILTER (WHERE NOT b.is_commerce) AS organic_avg_views,

  COUNT(*) FILTER (WHERE b.dialect = 'southern') AS southern_count,
  COUNT(*) FILTER (WHERE b.dialect = 'northern') AS northern_count,

  COUNT(*) FILTER (WHERE b.cta_type IS NOT NULL) * 100.0 /
    NULLIF(COUNT(*), 0) AS has_cta_pct,

  -- Distribution annotation norms (mirrors niche_intelligence).
  COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags IS NOT NULL), 0)
    AS pct_has_specific_hashtags,
  COUNT(*) FILTER (WHERE b.has_caption_text = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.has_caption_text IS NOT NULL), 0)
    AS pct_has_caption_text,
  AVG(b.hashtag_count) AS avg_hashtag_count,
  COUNT(*) FILTER (WHERE b.is_original_sound = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.is_original_sound IS NOT NULL), 0)
    AS pct_original_sound,

  -- Median shot count (PR2 anchor for ritual prompt v2 used scene_count
  -- median; same field exposed at content_class level for video diagnosis
  -- and pattern thesis benchmarks).
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.scene_count) AS median_scene_count,

  NOW() AS computed_at
FROM base b
LEFT JOIN hook_dist h ON h.content_class_id = b.content_class_id
LEFT JOIN tone_dist t ON t.content_class_id = b.content_class_id
GROUP BY b.content_class_id, h.hook_distribution, t.tone_distribution;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_intelligence_pk
  ON content_class_intelligence(content_class_id);

GRANT SELECT ON content_class_intelligence TO authenticated;

-- ── Refresh function ────────────────────────────────────────────────
-- Cloud Run batch ingest calls this after each corpus update (mirrors
-- ``refresh_niche_intelligence``). SECURITY DEFINER so it runs as the
-- function owner (service_role); locked down from anon/authenticated.

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

COMMIT;
