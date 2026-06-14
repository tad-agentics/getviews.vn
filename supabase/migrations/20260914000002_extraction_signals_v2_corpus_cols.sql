-- Extraction signals v2 — nullable benchmark columns on video_corpus (Tier 1).

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS time_to_first_value_sec DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS loop_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS words_per_sec DOUBLE PRECISION;

COMMENT ON COLUMN video_corpus.time_to_first_value_sec IS
  'Seconds to first content word after hook window (Tier 1 info-density).';
COMMENT ON COLUMN video_corpus.loop_score IS
  'Deterministic loop-ability score 0–1 (Tier 1).';
COMMENT ON COLUMN video_corpus.words_per_sec IS
  'Overall spoken words per second (Tier 1 info-density).';
