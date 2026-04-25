-- Ordered creator niche picks (min 3 enforced in app for new saves).
-- primary_niche remains the first / “focus” niche; app keeps it in sync with niche_ids[1].
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS niche_ids integer[];

COMMENT ON COLUMN public.profiles.niche_ids IS
  'Ordered niche_taxonomy ids. When length >= 3, primary_niche should match the first element. Legacy rows may only have primary_niche.';
