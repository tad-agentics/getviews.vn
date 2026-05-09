-- PR6 deep sweep (2026-07-10): remove any remaining ``profiles`` triggers whose
-- function body still references the dropped ``primary_niche`` column.
--
-- ``20260701000001`` / ``20260630000002`` already DROP named objects; hosted DBs
-- can still hit ``42703 column profiles.primary_niche does not exist`` if a
-- differently named trigger was added manually, or a migration replay left stale
-- metadata. This migration is fully idempotent.
--
-- 1) Known artifacts (repeat — harmless if already gone)
DROP TRIGGER IF EXISTS trg_invalidate_creator_velocity_match_score
  ON public.profiles;

DROP FUNCTION IF EXISTS public.invalidate_creator_velocity_match_score();

DROP TRIGGER IF EXISTS trg_profiles_sync_primary_niche_from_niche_ids
  ON public.profiles;

DROP FUNCTION IF EXISTS public.sync_profile_primary_niche_from_niche_ids() CASCADE;

-- 2) Any other user triggers on ``public.profiles`` whose pl/pgSQL source
-- mentions primary_niche (legacy column sync / invalidation helpers).
DO $sweep$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT t.tgname AS trigger_name
    FROM pg_trigger t
    JOIN pg_proc p ON t.tgfoid = p.oid
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_namespace ns ON c.relnamespace = ns.oid
    WHERE ns.nspname = 'public'
      AND c.relname = 'profiles'
      AND NOT t.tgisinternal
      AND p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
      AND p.prosrc ILIKE '%primary_niche%'
  LOOP
    EXECUTE format(
      'DROP TRIGGER IF EXISTS %I ON public.profiles',
      r.trigger_name
    );
    RAISE NOTICE 'pr6_deep_sweep: dropped trigger % on public.profiles',
      r.trigger_name;
  END LOOP;
END;
$sweep$;
