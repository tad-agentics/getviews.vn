-- B.4.1 — scene_intelligence: per-(niche, scene_type) aggregates for /app/script
-- Refreshed by Cloud Run batch (``getviews_pipeline.scene_intelligence_refresh``).

CREATE TABLE IF NOT EXISTS scene_intelligence (
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id) ON DELETE CASCADE,
  scene_type TEXT NOT NULL,
  corpus_avg_duration NUMERIC(6, 2),
  winner_avg_duration NUMERIC(6, 2),
  winner_overlay_style TEXT,
  overlay_samples JSONB NOT NULL DEFAULT '[]'::jsonb,
  tip TEXT,
  reference_video_ids TEXT[] NOT NULL DEFAULT '{}'::text[],
  sample_size INTEGER NOT NULL DEFAULT 0,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (niche_id, scene_type)
);

CREATE INDEX IF NOT EXISTS idx_scene_intelligence_niche ON scene_intelligence (niche_id);

ALTER TABLE scene_intelligence ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read scene_intelligence"
  ON scene_intelligence FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

COMMENT ON TABLE scene_intelligence IS
  'B.4 — Aggregated scene durations + overlay hints per niche (nightly refresh; min sample in app logic).';
