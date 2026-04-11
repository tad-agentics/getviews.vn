-- Add 30 classification columns + 15 indexes to video_corpus
-- Enables queryable filtering + aggregation by hook_type, format, dialect, commerce, etc.
-- Also replaces the thin niche_intelligence materialized view with the full Vietnamese-optimized version.

-- ── Group A: Gemini analysis extraction (11 new columns; breakout_multiplier already added) ──
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS hook_type TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS hook_phrase TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS face_appears_at REAL;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS first_frame_type TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS video_duration REAL;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS transitions_per_second REAL;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS tone TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS text_overlay_count INTEGER DEFAULT 0;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS scene_count INTEGER DEFAULT 0;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'vi';

-- ── Group B: Vietnamese/Asian TikTok-specific (4 columns) ──
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS content_format TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS cta_type TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS is_commerce BOOLEAN DEFAULT FALSE;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS dialect TEXT;

-- ── Group C: ED metadata (already fetched, now stored) (13 columns) ──
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS saves BIGINT DEFAULT 0;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS save_rate REAL;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS posting_hour INTEGER;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS sound_id TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS sound_name TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS is_original_sound BOOLEAN;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS creator_followers BIGINT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS creator_tier TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS caption TEXT;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS hashtags TEXT[];
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS is_stitch BOOLEAN DEFAULT FALSE;
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS is_duet BOOLEAN DEFAULT FALSE;

-- ── Group D: Searchable text (2 columns) ──
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS topics TEXT[];
ALTER TABLE video_corpus ADD COLUMN IF NOT EXISTS transcript_snippet TEXT;

-- ── Indexes for queries that matter ──
CREATE INDEX IF NOT EXISTS idx_corpus_hook_type ON video_corpus(niche_id, hook_type);
CREATE INDEX IF NOT EXISTS idx_corpus_face_timing ON video_corpus(niche_id, face_appears_at);
CREATE INDEX IF NOT EXISTS idx_corpus_tone ON video_corpus(niche_id, tone);
CREATE INDEX IF NOT EXISTS idx_corpus_first_frame ON video_corpus(niche_id, first_frame_type);
CREATE INDEX IF NOT EXISTS idx_corpus_duration ON video_corpus(niche_id, video_duration);
CREATE INDEX IF NOT EXISTS idx_corpus_format ON video_corpus(niche_id, content_format);
CREATE INDEX IF NOT EXISTS idx_corpus_commerce ON video_corpus(niche_id, is_commerce) WHERE is_commerce = TRUE;
CREATE INDEX IF NOT EXISTS idx_corpus_save_rate ON video_corpus(niche_id, save_rate DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_corpus_posting_hour ON video_corpus(niche_id, posting_hour);
CREATE INDEX IF NOT EXISTS idx_corpus_sound ON video_corpus(sound_id) WHERE sound_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_corpus_creator_tier ON video_corpus(niche_id, creator_tier);
CREATE INDEX IF NOT EXISTS idx_corpus_posted_at ON video_corpus(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_hashtags ON video_corpus USING GIN(hashtags);
CREATE INDEX IF NOT EXISTS idx_corpus_topics ON video_corpus USING GIN(topics);

-- ── Replace thin niche_intelligence with full Vietnamese-optimized view ──
DROP MATERIALIZED VIEW IF EXISTS niche_intelligence CASCADE;

CREATE MATERIALIZED VIEW niche_intelligence AS
WITH base AS (
  SELECT * FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
),
hook_dist AS (
  SELECT niche_id, jsonb_object_agg(hook_type, cnt) as hook_distribution
  FROM (SELECT niche_id, hook_type, COUNT(*) as cnt FROM base WHERE hook_type IS NOT NULL GROUP BY niche_id, hook_type) x
  GROUP BY niche_id
),
format_dist AS (
  SELECT niche_id, jsonb_object_agg(content_format, cnt) as format_distribution
  FROM (SELECT niche_id, content_format, COUNT(*) as cnt FROM base WHERE content_format IS NOT NULL GROUP BY niche_id, content_format) x
  GROUP BY niche_id
),
tone_dist AS (
  SELECT niche_id, jsonb_object_agg(tone, cnt) as tone_distribution
  FROM (SELECT niche_id, tone, COUNT(*) as cnt FROM base WHERE tone IS NOT NULL GROUP BY niche_id, tone) x
  GROUP BY niche_id
)
SELECT
  b.niche_id,
  COUNT(*) as sample_size,
  COALESCE(h.hook_distribution, '{}'::jsonb) as hook_distribution,
  COALESCE(f.format_distribution, '{}'::jsonb) as format_distribution,
  COALESCE(t.tone_distribution, '{}'::jsonb) as tone_distribution,
  AVG(b.face_appears_at) FILTER (WHERE b.face_appears_at IS NOT NULL) as avg_face_appears_at,
  COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL AND b.face_appears_at <= 0.5) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL), 0) as pct_face_in_half_sec,
  AVG(b.transitions_per_second) as avg_transitions_per_second,
  AVG(b.video_duration) as avg_duration,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.video_duration) as median_duration,
  MIN(b.video_duration) as min_duration,
  MAX(b.video_duration) as max_duration,
  AVG(b.engagement_rate) as avg_engagement_rate,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) as median_er,
  AVG(b.text_overlay_count) as avg_text_overlays,
  COUNT(*) FILTER (WHERE b.is_commerce) * 100.0 /
    NULLIF(COUNT(*), 0) as commerce_pct,
  AVG(b.views) FILTER (WHERE b.is_commerce) as commerce_avg_views,
  AVG(b.views) FILTER (WHERE NOT b.is_commerce) as organic_avg_views,
  COUNT(*) FILTER (WHERE b.dialect = 'southern') as southern_count,
  COUNT(*) FILTER (WHERE b.dialect = 'northern') as northern_count,
  COUNT(*) FILTER (WHERE b.cta_type IS NOT NULL) * 100.0 /
    NULLIF(COUNT(*), 0) as has_cta_pct,
  NOW() as computed_at
FROM base b
LEFT JOIN hook_dist h ON h.niche_id = b.niche_id
LEFT JOIN format_dist f ON f.niche_id = b.niche_id
LEFT JOIN tone_dist t ON t.niche_id = b.niche_id
GROUP BY b.niche_id, h.hook_distribution, f.format_distribution, t.tone_distribution;

CREATE UNIQUE INDEX idx_niche_intelligence_pk ON niche_intelligence(niche_id);

GRANT SELECT ON niche_intelligence TO authenticated;
