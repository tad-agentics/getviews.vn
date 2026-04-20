-- Phase C.2.1 — stub RPC; full implementation reads hook ranks from corpus / patterns.
-- Returns zero rows until C.2 wires video_patterns niche slices.

CREATE OR REPLACE FUNCTION public.pattern_wow_diff_7d(p_niche_id INT)
RETURNS TABLE (
  hook_type   TEXT,
  rank_now    INT,
  rank_prior  INT,
  rank_change INT,
  is_new      BOOLEAN,
  is_dropped  BOOLEAN
)
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT NULL::TEXT, NULL::INT, NULL::INT, NULL::INT, NULL::BOOLEAN, NULL::BOOLEAN
  WHERE FALSE;
$$;

GRANT EXECUTE ON FUNCTION public.pattern_wow_diff_7d(INT) TO authenticated, service_role;
