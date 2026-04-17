-- Allow anonymous (unauthenticated) users to read video_corpus and trending_cards
-- for the public landing page. These tables contain no PII.

-- video_corpus: add anon read alongside existing authenticated policy
DROP POLICY IF EXISTS "anon_read_corpus" ON video_corpus;
CREATE POLICY "anon_read_corpus"
  ON video_corpus FOR SELECT
  TO anon
  USING (true);

-- trending_cards: add anon read alongside existing authenticated policy
DROP POLICY IF EXISTS "anon_read_trending_cards" ON trending_cards;
CREATE POLICY "anon_read_trending_cards"
  ON trending_cards FOR SELECT
  TO anon
  USING (true);
