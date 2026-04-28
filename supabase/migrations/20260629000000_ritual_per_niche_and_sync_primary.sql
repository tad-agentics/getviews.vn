-- daily_ritual: allow one row per (user, date, niche) so the morning job can
-- write up to 3 ritual bundles (one per followed niche).
-- profiles: drive ``primary_niche`` from ``niche_ids[1]`` so server code and
-- legacy triggers keep a single derived column (no “focus niche” in product UI).

-- ── 1) daily_ritual composite primary key ─────────────────────────────
ALTER TABLE public.daily_ritual DROP CONSTRAINT IF EXISTS daily_ritual_pkey;

ALTER TABLE public.daily_ritual
  ADD PRIMARY KEY (user_id, generated_for_date, niche_id);

COMMENT ON TABLE public.daily_ritual IS
  'Tối đa một bộ 3 kịch bản / (user, ngày, niche_id) — tối đa 3 ngày theo 3 slot niche_ids.';

-- ── 2) Sync primary_niche from niche_ids[1] (1-based in Postgres arrays) ──
CREATE OR REPLACE FUNCTION public.sync_profile_primary_niche_from_niche_ids()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
  IF NEW.niche_ids IS NOT NULL AND coalesce(array_length(NEW.niche_ids, 1), 0) >= 1 THEN
    NEW.primary_niche := NEW.niche_ids[1];
  ELSE
    NEW.primary_niche := NULL;
  END IF;
  RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_profiles_sync_primary_niche_from_niche_ids ON public.profiles;
CREATE TRIGGER trg_profiles_sync_primary_niche_from_niche_ids
  BEFORE INSERT OR UPDATE OF niche_ids ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.sync_profile_primary_niche_from_niche_ids();

-- One-time backfill so old rows match niche_ids[1] before the app stops sending primary_niche
UPDATE public.profiles p
SET primary_niche = p.niche_ids[1]
WHERE p.niche_ids IS NOT NULL
  AND coalesce(array_length(p.niche_ids, 1), 0) >= 1
  AND p.primary_niche IS DISTINCT FROM p.niche_ids[1];

UPDATE public.profiles
SET primary_niche = NULL
WHERE niche_ids IS NULL
   OR coalesce(array_length(niche_ids, 1), 0) = 0;

-- Column comment: implementation detail, not a separate “ngách chính” in UX
COMMENT ON COLUMN public.profiles.primary_niche IS
  'Derived: niche_ids[1] when set (trigger). Legacy readers only.';

COMMENT ON COLUMN public.profiles.niche_ids IS
  'Up to 3 ordered niche picks — sole user-facing source for “ngách quan tâm”.';
