-- Corpus ingest criteria v1 — boost attribution + relaxation provenance

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS boost_attribution text NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS reference_eligible boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS ingest_relaxation_tier smallint NOT NULL DEFAULT 0;

COMMENT ON COLUMN video_corpus.boost_attribution IS
  'unknown | organic_confident | suspect_low | suspect_medium — §4.7 M1 heuristic';
COMMENT ON COLUMN video_corpus.reference_eligible IS
  'false when boost_attribution=suspect_medium — peer pool / MV hygiene';
COMMENT ON COLUMN video_corpus.ingest_relaxation_tier IS
  '0 strict | 1 recency/convergence relaxed | 2 view-floor relaxed (R1)';
