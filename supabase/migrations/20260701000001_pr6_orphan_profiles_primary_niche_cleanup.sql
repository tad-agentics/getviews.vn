-- PR6 follow-up (ops): remove any PostgreSQL objects that still reference
-- ``profiles.primary_niche`` after the column was dropped in
-- ``20260513000001_two_axis_niche_pr6_drop_primary_niche.sql``.
--
-- Symptom: Cloud Run morning ritual / admin trigger fails with PostgREST-style
-- ``42703 column profiles.primary_niche does not exist`` when a BEFORE/AFTER
-- trigger body still touches NEW.primary_niche, or a stale function remains.
--
-- Idempotent. Safe if ``20260613000000_drop_creator_velocity_match_score.sql``
-- and ``20260630000000_drop_primary_niche_sync_trigger_pr6.sql`` already ran.
--
-- NOTE: Must not share timestamp ``20260701000000`` with another migration —
-- ``schema_migrations.version`` is unique per numeric prefix only.

DROP TRIGGER IF EXISTS trg_invalidate_creator_velocity_match_score
  ON public.profiles;

DROP FUNCTION IF EXISTS public.invalidate_creator_velocity_match_score();

DROP TRIGGER IF EXISTS trg_profiles_sync_primary_niche_from_niche_ids
  ON public.profiles;

DROP FUNCTION IF EXISTS public.sync_profile_primary_niche_from_niche_ids() CASCADE;
