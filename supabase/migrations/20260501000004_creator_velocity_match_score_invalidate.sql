-- Phase D.1.3 — KOL match_score cache invalidation trigger
--
-- Background: creator_velocity.match_score is a best-effort cache for
-- compute_match_score() output in kol_browse.py. The score itself is
-- user-specific (depends on the requesting user's followers + reference
-- handles), but it is stored globally per (creator_handle, niche_id)
-- because niche-scope lookups are the dominant access pattern and the
-- recompute cost is O(creators-in-niche) anyway.
--
-- When a user's profile changes (primary_niche flip or reference_handles
-- edit), any cached score computed against the prior profile state is
-- stale for them. We null out rows in the affected niche(s) so the next
-- kol_browse call recomputes on demand. Other users in the same niche
-- will also see a recompute — acceptable because the cost is bounded
-- and the alternative (per-user cache) would require a new table with
-- O(users × creators-in-niche) rows.
--
-- Scope: the trigger touches only match_score + match_score_computed_at.
-- Other creator_velocity columns (velocity_score, avg_views, …) are
-- unaffected.

CREATE OR REPLACE FUNCTION public.invalidate_creator_velocity_match_score()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Only fire when the relevant profile fields actually change.
  IF (NEW.primary_niche IS DISTINCT FROM OLD.primary_niche)
     OR (NEW.reference_channel_handles IS DISTINCT FROM OLD.reference_channel_handles)
  THEN
    UPDATE public.creator_velocity
       SET match_score = NULL,
           match_score_computed_at = NULL
     WHERE niche_id IN (
       COALESCE(OLD.primary_niche, -1),
       COALESCE(NEW.primary_niche, -1)
     )
       AND (match_score IS NOT NULL OR match_score_computed_at IS NOT NULL);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_invalidate_creator_velocity_match_score ON public.profiles;

CREATE TRIGGER trg_invalidate_creator_velocity_match_score
AFTER UPDATE OF primary_niche, reference_channel_handles
ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.invalidate_creator_velocity_match_score();

COMMENT ON FUNCTION public.invalidate_creator_velocity_match_score() IS
  'D.1.3 — nulls creator_velocity.match_score in old+new niche when a profile primary_niche or reference_channel_handles flips.';
