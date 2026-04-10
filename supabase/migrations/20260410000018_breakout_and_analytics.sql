-- P1-7: Breakout multiplier + creator velocity analytics columns
--
-- Adds:
--   video_corpus.breakout_multiplier  — video views / creator avg_views (NULL until computed)
--   creator_velocity.avg_views        — mean views per video for this creator (from corpus)
--   creator_velocity.video_count      — how many corpus videos were used in the avg
--
-- Creator velocity rows are upserted weekly by batch_analytics.py.
-- breakout_multiplier is updated in the same weekly batch.

-- 1. breakout_multiplier on video_corpus
ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS breakout_multiplier FLOAT;

CREATE INDEX IF NOT EXISTS idx_corpus_breakout
  ON video_corpus (niche_id, breakout_multiplier DESC NULLS LAST);

-- 2. avg_views + video_count on creator_velocity
--    (existing table tracks engagement_trend, dominant_hook_type etc.; we extend it)
ALTER TABLE creator_velocity
  ADD COLUMN IF NOT EXISTS avg_views FLOAT,
  ADD COLUMN IF NOT EXISTS video_count INTEGER;

CREATE INDEX IF NOT EXISTS idx_creator_velocity_handle
  ON creator_velocity (creator_handle, niche_id);

-- 3. signal_grades table — P1-8: stores computed signal per (niche_id, hook_type, week_start)
--    Populated by signal_classifier.py weekly.
CREATE TABLE IF NOT EXISTS signal_grades (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id       INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  hook_type      TEXT NOT NULL,
  week_start     DATE NOT NULL,
  signal         TEXT NOT NULL CHECK (signal IN ('rising', 'early', 'stable', 'declining')),
  creator_count  INTEGER NOT NULL DEFAULT 0,
  total_views    BIGINT NOT NULL DEFAULT 0,
  sample_size    INTEGER NOT NULL DEFAULT 0,
  computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (niche_id, hook_type, week_start)
);

CREATE INDEX IF NOT EXISTS idx_signal_grades_niche_week
  ON signal_grades (niche_id, week_start DESC);

ALTER TABLE signal_grades ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read signal_grades"
  ON signal_grades FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);
