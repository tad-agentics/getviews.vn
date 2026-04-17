-- Add freshness tracking columns to niche_taxonomy.
-- last_hashtag_refresh: date of most recent Layer 0D freshness scan.
-- stale_signal_count: number of signal_hashtags not seen in corpus last 30 days.
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE niche_taxonomy
  ADD COLUMN IF NOT EXISTS last_hashtag_refresh DATE,
  ADD COLUMN IF NOT EXISTS stale_signal_count   INT DEFAULT 0;
