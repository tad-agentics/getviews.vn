-- 2026-05-05 — single-niche refactor (PR1 of 5).
--
-- Collapse the multi-niche profile model down to one niche per user.
-- Background:
--   - 20260410000012 introduced ``profiles.primary_niche`` (INTEGER FK).
--   - 20260525000000 added ``profiles.niche_ids integer[]`` for ordered
--     multi-niche follow lists. The morning-ritual cron capped at "max 3
--     niches per user" as a band-aid against runaway compute.
--   - Product decision (2026-05-05): one niche per user. Drives Home,
--     Trends default, flop baseline, KPI baselines. Browsing other
--     niches happens via Trends pills, not by following them.
--
-- This migration backfills primary_niche from niche_ids[1] for any row
-- that has only the array set, then drops the array column. The morning
-- ritual cron + FE simplification land in PR2 + PR3.
--
-- primary_niche stays nullable: pre-onboarding profiles legitimately
-- have NULL until they finish the niche picker. The /app/* layout
-- guard already redirects null-niche profiles into onboarding.
--
-- DBs that already applied 20260629000000_ritual_per_niche_and_sync_primary.sql
-- have ``trg_profiles_sync_primary_niche_from_niche_ids`` on ``niche_ids`` —
-- drop it before ``DROP COLUMN`` so ``supabase db push --include-all`` works.

DROP TRIGGER IF EXISTS trg_profiles_sync_primary_niche_from_niche_ids ON public.profiles;
DROP FUNCTION IF EXISTS public.sync_profile_primary_niche_from_niche_ids() CASCADE;

UPDATE public.profiles
SET primary_niche = niche_ids[1]
WHERE primary_niche IS NULL
  AND niche_ids IS NOT NULL
  AND array_length(niche_ids, 1) > 0;

ALTER TABLE public.profiles
  DROP COLUMN IF EXISTS niche_ids;

COMMENT ON COLUMN public.profiles.primary_niche IS
  'Single niche per user. Set during onboarding, editable in Settings (auto-regenerates daily ritual via POST /home/regenerate-ritual). NULL only between signup and onboarding completion.';
