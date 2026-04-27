-- Corpus + intelligence aggregates + llm_cache

CREATE TABLE IF NOT EXISTS video_corpus (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  video_id TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL CHECK (content_type IN ('video', 'carousel')),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  creator_handle TEXT NOT NULL,
  tiktok_url TEXT NOT NULL,
  thumbnail_url TEXT,
  video_url TEXT,
  frame_urls TEXT[] NOT NULL DEFAULT '{}',
  analysis_json JSONB NOT NULL,
  views BIGINT NOT NULL DEFAULT 0,
  likes BIGINT NOT NULL DEFAULT 0,
  comments BIGINT NOT NULL DEFAULT 0,
  shares BIGINT NOT NULL DEFAULT 0,
  engagement_rate NUMERIC(10, 4) NOT NULL DEFAULT 0,
  indexed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corpus_niche_date ON video_corpus (niche_id, indexed_at DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_niche_er ON video_corpus (niche_id, engagement_rate DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_content_type ON video_corpus (content_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_corpus_video_id ON video_corpus (video_id);

ALTER TABLE video_corpus ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read corpus"
  ON video_corpus FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE MATERIALIZED VIEW niche_intelligence AS
SELECT
  nt.id AS niche_id,
  AVG((NULLIF(v.analysis_json->>'face_appears_at', ''))::double precision) AS avg_face_appears_at,
  '{}'::jsonb AS hook_type_distribution,
  AVG((NULLIF(v.analysis_json->>'scene_transitions_per_second', ''))::double precision) AS avg_transitions_per_second,
  AVG((NULLIF(v.analysis_json->>'duration_seconds', ''))::double precision) AS avg_video_length_seconds,
  AVG(v.engagement_rate) AS median_engagement_rate,
  COUNT(v.id)::integer AS sample_size,
  COUNT(v.id) FILTER (WHERE v.indexed_at > now() - interval '7 days')::integer AS video_count_7d,
  '[]'::jsonb AS trending_keywords,
  now() AS computed_at
FROM niche_taxonomy nt
LEFT JOIN video_corpus v ON v.niche_id = nt.id
GROUP BY nt.id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_niche_intelligence_niche_id ON niche_intelligence (niche_id);

GRANT SELECT ON niche_intelligence TO authenticated;

CREATE TABLE IF NOT EXISTS trend_velocity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  week_start DATE NOT NULL,
  hook_type_shifts JSONB,
  format_changes JSONB,
  engagement_changes JSONB,
  new_hashtags TEXT[],
  sound_trends JSONB
);

CREATE INDEX IF NOT EXISTS idx_trend_velocity_niche_week ON trend_velocity (niche_id, week_start DESC);

ALTER TABLE trend_velocity ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read trend_velocity"
  ON trend_velocity FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE TABLE IF NOT EXISTS hook_effectiveness (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  hook_type TEXT NOT NULL,
  avg_views BIGINT,
  avg_engagement_rate NUMERIC(10, 4),
  avg_completion_rate NUMERIC(10, 4),
  sample_size INTEGER,
  trend_direction TEXT CHECK (trend_direction IN ('rising', 'stable', 'declining')),
  computed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_hook_effectiveness_niche ON hook_effectiveness (niche_id, computed_at DESC);

ALTER TABLE hook_effectiveness ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read hook_effectiveness"
  ON hook_effectiveness FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE TABLE IF NOT EXISTS format_lifecycle (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  format_type TEXT NOT NULL,
  lifecycle_stage TEXT CHECK (lifecycle_stage IN ('emerging', 'peaking', 'declining')),
  volume_trend NUMERIC,
  engagement_trend NUMERIC,
  weeks_in_stage INTEGER,
  computed_at TIMESTAMPTZ
);

ALTER TABLE format_lifecycle ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read format_lifecycle"
  ON format_lifecycle FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE TABLE IF NOT EXISTS creator_velocity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  creator_handle TEXT NOT NULL,
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  follower_trajectory JSONB,
  engagement_trend TEXT CHECK (engagement_trend IN ('rising', 'stable', 'declining')),
  dominant_hook_type TEXT,
  dominant_format TEXT,
  posting_frequency_per_week NUMERIC,
  velocity_score NUMERIC,
  computed_at TIMESTAMPTZ
);

ALTER TABLE creator_velocity ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read creator_velocity"
  ON creator_velocity FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE TABLE IF NOT EXISTS batch_failures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  video_id TEXT NOT NULL,
  error_type TEXT NOT NULL,
  failure_count INTEGER NOT NULL DEFAULT 1,
  last_failed_at TIMESTAMPTZ,
  excluded_permanently BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE batch_failures ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS llm_cache (
  input_hash TEXT PRIMARY KEY,
  response JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE llm_cache ENABLE ROW LEVEL SECURITY;

-- Block direct client access; Edge Functions use service_role (bypasses RLS)
