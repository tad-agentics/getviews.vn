-- Idempotent repair: migration 20260525000000 may be recorded as applied while
-- ``profiles.niche_ids`` never existed (repair/history drift). Safe no-op when column exists.
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS niche_ids integer[];

COMMENT ON COLUMN public.profiles.niche_ids IS
  'Ordered niche_taxonomy ids. When length >= 3, primary_niche should match the first element. Legacy rows may only have primary_niche.';
