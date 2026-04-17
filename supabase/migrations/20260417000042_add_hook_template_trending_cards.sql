-- Add hook_template: a fillable formula derived from the top corpus videos.
-- NULL for cards generated before this migration (backfilled on next weekly batch).
ALTER TABLE trending_cards ADD COLUMN IF NOT EXISTS hook_template TEXT;
