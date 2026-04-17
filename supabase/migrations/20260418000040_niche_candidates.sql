-- niche_candidates: staging table for hashtags Gemini couldn't confidently
-- assign to a niche. Human-reviewable queue for potential new niches or
-- signal expansion.
-- Idempotent: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS,
-- policies use IF NOT EXISTS guard via DO $$ blocks.

CREATE TABLE IF NOT EXISTS niche_candidates (
  id                BIGSERIAL PRIMARY KEY,
  hashtag           TEXT NOT NULL UNIQUE,
  occurrences       INT DEFAULT 1,
  avg_views         INT DEFAULT 0,
  sample_video_ids  TEXT[] DEFAULT '{}',
  discovery_date    DATE NOT NULL DEFAULT CURRENT_DATE,
  reviewed          BOOLEAN DEFAULT false,
  assigned_niche_id INT REFERENCES niche_taxonomy(id),
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_niche_candidates_unreviewed
  ON niche_candidates (occurrences DESC)
  WHERE reviewed = false;

ALTER TABLE niche_candidates ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'niche_candidates' AND policyname = 'Service write'
  ) THEN
    CREATE POLICY "Service write" ON niche_candidates
      FOR ALL USING (auth.role() = 'service_role');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'niche_candidates' AND policyname = 'Public read'
  ) THEN
    CREATE POLICY "Public read" ON niche_candidates
      FOR SELECT USING (true);
  END IF;
END $$;
