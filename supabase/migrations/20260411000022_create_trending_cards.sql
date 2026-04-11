-- P1-9: Trending This Week — curated cards per niche/signal (weekly batch)

CREATE TABLE IF NOT EXISTS trending_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  signal TEXT NOT NULL CHECK (signal IN ('rising', 'early', 'stable', 'declining')),
  hook_type TEXT,
  video_ids TEXT[] NOT NULL DEFAULT '{}',
  corpus_cite TEXT,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  week_of DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trending_cards_niche_week ON trending_cards (niche_id, week_of DESC);
CREATE INDEX IF NOT EXISTS idx_trending_cards_week ON trending_cards (week_of DESC);

ALTER TABLE trending_cards ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trending_cards_select" ON trending_cards;
CREATE POLICY "trending_cards_select"
  ON trending_cards FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "trending_cards_service" ON trending_cards;
CREATE POLICY "trending_cards_service"
  ON trending_cards FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
