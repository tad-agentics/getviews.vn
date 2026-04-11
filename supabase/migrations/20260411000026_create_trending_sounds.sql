-- U3: Sound Intelligence — weekly trending sounds per niche (Cloud Run batch)

CREATE TABLE IF NOT EXISTS trending_sounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INT REFERENCES niche_taxonomy(id) ON DELETE CASCADE,
  sound_id TEXT NOT NULL,
  sound_name TEXT NOT NULL,
  usage_count INT NOT NULL DEFAULT 0,
  is_original_sound BOOLEAN NOT NULL DEFAULT false,
  total_views BIGINT NOT NULL DEFAULT 0,
  commerce_signal BOOLEAN NOT NULL DEFAULT false,
  week_of DATE NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_sounds_niche_sound_week
  ON trending_sounds(niche_id, sound_id, week_of);

CREATE INDEX IF NOT EXISTS idx_trending_sounds_week ON trending_sounds(week_of DESC);

ALTER TABLE trending_sounds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read trending_sounds" ON trending_sounds
  FOR SELECT USING (true);
