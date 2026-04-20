-- Phase C.4.1 — weeks at #1 for (day, hour_bucket); stub returns 0 until timing aggregates land.

CREATE OR REPLACE FUNCTION public.timing_top_window_streak(
  p_niche_id INT,
  p_day INT,
  p_hour_bucket INT
) RETURNS INTEGER
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT 0::INTEGER;
$$;

GRANT EXECUTE ON FUNCTION public.timing_top_window_streak(INT, INT, INT) TO authenticated, service_role;
