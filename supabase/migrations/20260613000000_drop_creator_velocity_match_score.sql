-- Drop ``creator_velocity.match_score`` cache columns + invalidation trigger
-- ────────────────────────────────────────────────────────────────────────────
--
-- Background. ``match_score`` + ``match_score_computed_at`` were added in
-- migration ``20260430000006_creator_velocity_match_score.sql`` as a cache
-- for ``compute_match_score()`` output in ``kol_browse.py``. The KOL browse
-- screen was retired during the Creator-only pivot, and ``kol_browse.py``
-- itself was deleted in PR #280 (chore: remove kol_browse dead code).
--
-- After that deletion these columns can never be written again — only the
-- trigger ``trg_invalidate_creator_velocity_match_score`` on ``public.profiles``
-- (added in migration ``20260501000004_creator_velocity_match_score_invalidate``)
-- still touches them, and only to set them to NULL when a profile flips
-- ``primary_niche`` or ``reference_channel_handles``. Pure carrying cost
-- (one row update per profile-flip × the niche-affected rows) for data
-- nobody reads.
--
-- Drop order matters:
--   1. Drop the trigger (depends on the function).
--   2. Drop the function (no longer referenced anywhere).
--   3. Drop the columns (no longer referenced anywhere — verified via
--      grep across cloud-run/, src/, supabase/migrations/).
--
-- The earlier ALTER FUNCTION on this function in
-- ``20260504000006_phase5_secdef_search_path.sql`` (the SECDEF
-- search_path hardening sweep) becomes a historical no-op once this
-- migration runs — replaying that file on a fresh DB will fail unless
-- the function still exists, but Supabase migrations only ever apply
-- once in order, so the historical apply is unaffected.

-- 1. Drop the invalidation trigger from public.profiles.
DROP TRIGGER IF EXISTS trg_invalidate_creator_velocity_match_score
    ON public.profiles;

-- 2. Drop the function the trigger called.
DROP FUNCTION IF EXISTS public.invalidate_creator_velocity_match_score();

-- 3. Drop the orphan cache columns from creator_velocity.
ALTER TABLE public.creator_velocity
    DROP COLUMN IF EXISTS match_score,
    DROP COLUMN IF EXISTS match_score_computed_at;
