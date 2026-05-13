-- Phase 5.1b — provenance tracking for video_corpus rows.
--
-- Adds three columns that record HOW and WHEN a row entered the corpus:
--   ingest_source:   'batch_nightly' | 'user_diagnosis' | 'douyin_batch'
--   first_seen_at:   timestamp of the first insertion (never overwritten)
--   last_refreshed_at: timestamp of the most recent upsert/refresh
--
-- Used by:
--   services/corpus_quality.py — filters high-quality rows for cohort queries.
--   Phase 6.2 — COALESCE on UPSERT so batch doesn't overwrite user_diagnosis provenance.

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS ingest_source TEXT
    CHECK (ingest_source IN ('batch_nightly', 'user_diagnosis', 'douyin_batch')),
  ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_refreshed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS quality_tier TEXT
    CHECK (quality_tier IN ('high', 'medium', 'low'));

-- Back-fill existing batch rows (safe; won't touch future user_diagnosis rows).
UPDATE video_corpus
SET
  ingest_source = 'batch_nightly',
  quality_tier = 'high',
  first_seen_at = COALESCE(indexed_at, created_at),
  last_refreshed_at = COALESCE(indexed_at, created_at)
WHERE ingest_source IS NULL;

-- Index for filtering by source (used by cohort quality gate in Phase 5.4).
CREATE INDEX IF NOT EXISTS idx_corpus_ingest_source ON video_corpus (ingest_source);
