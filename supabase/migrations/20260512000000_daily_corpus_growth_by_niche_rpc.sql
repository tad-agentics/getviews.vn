-- 2026-05-12 — RPC for the daily health digest's corpus-growth section.
--
-- Wave 5+ residual. The cron-daily-health-digest Edge function pulls
-- "videos added in the last 24h, per niche" via this RPC. We use an
-- RPC (not inline PostgREST) because the per-niche aggregate joins
-- video_corpus → niche_taxonomy and the discriminated columns
-- (name_en / name_vn) need server-side coalescing — pushing that
-- into the JS function would mean two round-trips + client-side
-- joining a table the digest doesn't otherwise need.
--
-- The function is parameterized on ``p_since`` so backfill / debug
-- runs can pull arbitrary windows without a code change.
--
-- Returns one row per niche that had ≥ 1 row added since p_since,
-- sorted DESC so callers can just .slice(0, 5) for a top-5.
-- Niches with zero growth are intentionally excluded (would just
-- bloat the digest).
--
-- Security: SECURITY DEFINER + service_role-only EXECUTE so
-- anonymous / authenticated callers can't probe corpus deltas
-- through the public PostgREST surface.

CREATE OR REPLACE FUNCTION public.daily_corpus_growth_by_niche(
  p_since TIMESTAMPTZ
)
RETURNS TABLE (
  niche_id INT,
  niche_name TEXT,
  delta_24h BIGINT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    vc.niche_id,
    COALESCE(nt.name_en, nt.name_vn, vc.niche_id::text) AS niche_name,
    COUNT(*) AS delta_24h
  FROM public.video_corpus vc
  LEFT JOIN public.niche_taxonomy nt ON nt.id = vc.niche_id
  WHERE vc.indexed_at >= p_since
    AND vc.niche_id IS NOT NULL
  GROUP BY vc.niche_id, nt.name_en, nt.name_vn
  ORDER BY COUNT(*) DESC;
$$;

REVOKE ALL ON FUNCTION public.daily_corpus_growth_by_niche(TIMESTAMPTZ) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.daily_corpus_growth_by_niche(TIMESTAMPTZ) FROM anon;
REVOKE ALL ON FUNCTION public.daily_corpus_growth_by_niche(TIMESTAMPTZ) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.daily_corpus_growth_by_niche(TIMESTAMPTZ) TO service_role;

COMMENT ON FUNCTION public.daily_corpus_growth_by_niche(TIMESTAMPTZ) IS
  'Wave 5+ — per-niche video_corpus delta since p_since. Used by '
  'cron-daily-health-digest. Service-role only.';
