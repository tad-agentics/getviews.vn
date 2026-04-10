-- Explore: standardize corpus read policy + index for sort-by-views within niche
-- Note: idx_corpus_niche_date and idx_corpus_niche_er (005) already cover
-- (niche_id, indexed_at DESC) and (niche_id, engagement_rate DESC).

ALTER TABLE video_corpus ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read corpus" ON video_corpus;
DROP POLICY IF EXISTS "authenticated_read_corpus" ON video_corpus;

CREATE POLICY "authenticated_read_corpus"
  ON video_corpus FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_video_corpus_niche_views ON video_corpus (niche_id, views DESC);
