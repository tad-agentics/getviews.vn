-- Audit 2026-06-10 M-4: corpus browse (useVideoCorpus.ts) filters on
-- content_class_id + indexed_at range / views floor, but only a
-- single-column partial index on content_class_id existed — every browse
-- with a date or views filter re-sorted the class slice. Composite
-- indexes keep these paginated queries index-only as the corpus grows
-- (~10K rows today, +1K/week from nightly ingest).

CREATE INDEX IF NOT EXISTS idx_video_corpus_class_indexed
  ON video_corpus (content_class_id, indexed_at DESC)
  WHERE content_class_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_video_corpus_class_views
  ON video_corpus (content_class_id, views DESC)
  WHERE content_class_id IS NOT NULL;
