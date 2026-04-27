-- video_patterns — cross-video creative-formula clustering.
-- See artifacts/docs/features/viral-pattern-fingerprint.md for the design.
--
-- Nightly job computes a signature per video (hook_type + content_arc + tone +
-- energy_level + tps_bucket + face_first + has_text_overlay), hashes it, upserts
-- a row here, and stamps video_corpus.pattern_id so downstream intents can say
-- "this is instance #N of pattern X" without re-clustering at read time.
--
-- This migration sets up the table + column only. The clustering job lives in
-- cloud-run/getviews_pipeline/pattern_fingerprint.py (to be added in a follow-
-- up PR); until that job runs, pattern_id stays NULL and queries gracefully
-- degrade to the single-video narrative.

CREATE TABLE IF NOT EXISTS video_patterns (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signature_hash              TEXT NOT NULL UNIQUE,
  signature                   JSONB NOT NULL,
  display_name                TEXT,
  first_seen_at               TIMESTAMPTZ NOT NULL,
  last_seen_at                TIMESTAMPTZ NOT NULL,
  instance_count              INTEGER NOT NULL DEFAULT 0,
  niche_spread                INTEGER[] NOT NULL DEFAULT '{}',
  weekly_instance_count       INTEGER NOT NULL DEFAULT 0,
  weekly_instance_count_prev  INTEGER NOT NULL DEFAULT 0,
  is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
  computed_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS video_patterns_signature_hash_idx ON video_patterns (signature_hash);
CREATE INDEX IF NOT EXISTS video_patterns_last_seen_idx     ON video_patterns (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS video_patterns_weekly_delta_idx  ON video_patterns
  ((weekly_instance_count - weekly_instance_count_prev) DESC);

ALTER TABLE video_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read video_patterns"
  ON video_patterns FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

-- Link column on video_corpus. NULL until the clustering job runs.
ALTER TABLE video_corpus ADD COLUMN pattern_id UUID REFERENCES video_patterns(id);
CREATE INDEX IF NOT EXISTS video_corpus_pattern_id_idx ON video_corpus (pattern_id)
  WHERE pattern_id IS NOT NULL;
