-- Phase C.8.3 — KOL match_score cache

ALTER TABLE public.creator_velocity
  ADD COLUMN IF NOT EXISTS match_score INTEGER,
  ADD COLUMN IF NOT EXISTS match_score_computed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.creator_velocity.match_score IS 'Cached 0–100 match vs user profile; refreshed <7d';
