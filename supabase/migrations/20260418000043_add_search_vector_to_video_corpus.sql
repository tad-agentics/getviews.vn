-- Full-text search vector over hook_phrase + creator_handle.
-- 'simple' config: lowercase only, no stemming — correct for Vietnamese.
-- STORED: materialised on write, zero cost at query time.

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector(
      'simple',
      coalesce(hook_phrase, '') || ' ' || coalesce(creator_handle, '')
    )
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_corpus_search_vector
  ON video_corpus USING GIN(search_vector);
