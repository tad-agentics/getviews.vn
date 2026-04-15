-- Layer 0B output: Vietnamese "why this sound works" paragraph per trending sound
ALTER TABLE trending_sounds
  ADD COLUMN IF NOT EXISTS sound_insight_text TEXT;
