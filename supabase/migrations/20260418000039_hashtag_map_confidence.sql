-- Add confidence column to hashtag_niche_map for discovery pipeline.
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE hashtag_niche_map
  ADD COLUMN IF NOT EXISTS confidence TEXT
    CHECK (confidence IN ('high', 'medium', 'low', 'generic', 'candidate'))
    DEFAULT NULL;

-- Backfill: seed rows are always high confidence.
UPDATE hashtag_niche_map SET confidence = 'high' WHERE source = 'seed' AND confidence IS NULL;
