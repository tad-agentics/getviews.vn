-- P1-10: Meta-pattern Monday email — meta_insight on cards + RPC for digest

ALTER TABLE trending_cards ADD COLUMN IF NOT EXISTS meta_insight TEXT;

CREATE OR REPLACE FUNCTION get_weekly_trend_summaries(p_week_of DATE)
RETURNS TABLE (
  niche_name TEXT,
  top_signal TEXT,
  top_hook_type TEXT,
  card_count INT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    nt.name_vn AS niche_name,
    tc.signal AS top_signal,
    tc.hook_type AS top_hook_type,
    COUNT(*)::INT AS card_count
  FROM trending_cards tc
  JOIN niche_taxonomy nt ON nt.id = tc.niche_id
  WHERE tc.week_of = p_week_of
  GROUP BY nt.name_vn, tc.signal, tc.hook_type
  ORDER BY card_count DESC;
$$;

REVOKE ALL ON FUNCTION get_weekly_trend_summaries(DATE) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION get_weekly_trend_summaries(DATE) TO service_role;
