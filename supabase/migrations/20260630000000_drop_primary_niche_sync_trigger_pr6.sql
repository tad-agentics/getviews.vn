-- PR6 follow-up: remove any leftover ``primary_niche`` sync trigger/function.
--
-- ``profiles.primary_niche`` was dropped in ``20260513000001``. The
-- conditional block in ``20260629000001`` only (re)creates the sync
-- trigger when that column still exists — but hosted DBs that received
-- the trigger from an earlier partial apply, or manual DDL, can end up
-- with a trigger body that still assigns ``NEW.primary_niche`` after the
-- column is gone, surfacing Postgres ``42703`` on unrelated profile writes
-- or confusing operators when batch jobs fail.
--
-- Idempotent: DROP IF EXISTS only.

DROP TRIGGER IF EXISTS trg_profiles_sync_primary_niche_from_niche_ids
  ON public.profiles;

DROP FUNCTION IF EXISTS public.sync_profile_primary_niche_from_niche_ids() CASCADE;
