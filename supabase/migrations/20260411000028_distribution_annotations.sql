-- Add 3 distribution annotation columns to video_corpus.
-- These are NOT quality gates — every row is still ingested.
-- They annotate each video for corpus intelligence queries and feed
-- into niche_intelligence so synthesis can make data-backed distribution claims.
--
-- has_vietnamese_hashtags: True = at least 1 hashtag NOT in the generic TikTok list
--   (name is legacy from early design; semantically means "has_specific_hashtags")
-- has_caption_text:        True = caption contains ≥10 chars of non-hashtag text
-- hashtag_count:           total number of hashtags on the post

ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS has_vietnamese_hashtags BOOLEAN;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS has_caption_text BOOLEAN;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS hashtag_count INTEGER;

CREATE INDEX IF NOT EXISTS idx_corpus_specific_hashtags
  ON video_corpus(niche_id, has_vietnamese_hashtags)
  WHERE has_vietnamese_hashtags IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_corpus_caption_text
  ON video_corpus(niche_id, has_caption_text)
  WHERE has_caption_text IS NOT NULL;

-- ── Refresh niche_intelligence to add distribution norms ──────────────────────
-- Drop + recreate (materialized view columns cannot be added incrementally).
-- Adds 4 new aggregation columns:
--   pct_has_specific_hashtags — % of top videos with ≥1 niche-specific hashtag
--   pct_has_caption_text      — % of top videos with real caption text beyond hashtags
--   avg_hashtag_count         — average number of hashtags per video
--   pct_original_sound        — % of top videos using original sound (creator-composed)
-- These enable diagnosis claims like:
--   "92% top video trong ngách skincare có caption + hashtag cụ thể.
--    Video bạn chỉ có 4 hashtag tiếng Anh chung chung — thuật toán không biết đẩy cho ai."

DROP MATERIALIZED VIEW IF EXISTS niche_intelligence CASCADE;

CREATE MATERIALIZED VIEW niche_intelligence AS
WITH base AS (
  SELECT * FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
),
hook_dist AS (
  SELECT niche_id, jsonb_object_agg(hook_type, cnt) AS hook_distribution
  FROM (
    SELECT niche_id, hook_type, COUNT(*) AS cnt
    FROM base WHERE hook_type IS NOT NULL
    GROUP BY niche_id, hook_type
  ) x
  GROUP BY niche_id
),
format_dist AS (
  SELECT niche_id, jsonb_object_agg(content_format, cnt) AS format_distribution
  FROM (
    SELECT niche_id, content_format, COUNT(*) AS cnt
    FROM base WHERE content_format IS NOT NULL
    GROUP BY niche_id, content_format
  ) x
  GROUP BY niche_id
),
tone_dist AS (
  SELECT niche_id, jsonb_object_agg(tone, cnt) AS tone_distribution
  FROM (
    SELECT niche_id, tone, COUNT(*) AS cnt
    FROM base WHERE tone IS NOT NULL
    GROUP BY niche_id, tone
  ) x
  GROUP BY niche_id
)
SELECT
  b.niche_id,
  COUNT(*) AS sample_size,
  COALESCE(h.hook_distribution, '{}'::jsonb) AS hook_distribution,
  COALESCE(f.format_distribution, '{}'::jsonb) AS format_distribution,
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
  AVG(b.text_overlay_count) AS avg_text_overlays,
  COUNT(*) FILTER (WHERE b.is_commerce) * 100.0 /
    NULLIF(COUNT(*), 0) AS commerce_pct,
  AVG(b.views) FILTER (WHERE b.is_commerce) AS commerce_avg_views,
  AVG(b.views) FILTER (WHERE NOT b.is_commerce) AS organic_avg_views,
  COUNT(*) FILTER (WHERE b.dialect = 'southern') AS southern_count,
  COUNT(*) FILTER (WHERE b.dialect = 'northern') AS northern_count,
  COUNT(*) FILTER (WHERE b.cta_type IS NOT NULL) * 100.0 /
    NULLIF(COUNT(*), 0) AS has_cta_pct,

  -- ── Distribution annotation norms (new) ──────────────────────────────────
  -- Percentage of top videos that use ≥1 niche-specific hashtag (not generic).
  -- Null when no rows have the column populated (pre-backfill corpus).
  COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags IS NOT NULL), 0)
    AS pct_has_specific_hashtags,

  -- Percentage of top videos that have real caption text beyond hashtags.
  COUNT(*) FILTER (WHERE b.has_caption_text = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.has_caption_text IS NOT NULL), 0)
    AS pct_has_caption_text,

  -- Average hashtag count — benchmark for hashtag volume norms per niche.
  AVG(b.hashtag_count) AS avg_hashtag_count,

  -- Percentage using original sound (creator-composed vs trending sound).
  COUNT(*) FILTER (WHERE b.is_original_sound = TRUE) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.is_original_sound IS NOT NULL), 0)
    AS pct_original_sound,

  NOW() AS computed_at
FROM base b
LEFT JOIN hook_dist h ON h.niche_id = b.niche_id
LEFT JOIN format_dist f ON f.niche_id = b.niche_id
LEFT JOIN tone_dist t ON t.niche_id = b.niche_id
GROUP BY b.niche_id, h.hook_distribution, f.format_distribution, t.tone_distribution;

CREATE UNIQUE INDEX idx_niche_intelligence_pk ON niche_intelligence(niche_id);

GRANT SELECT ON niche_intelligence TO authenticated;
