-- P2-11: Cross-creator pattern detection (weekly batch, 7-day rolling window)

CREATE TABLE IF NOT EXISTS cross_creator_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy (id) ON DELETE CASCADE,
  hook_type TEXT NOT NULL,
  creator_count INTEGER NOT NULL,
  total_views BIGINT NOT NULL,
  creators TEXT[] NOT NULL DEFAULT '{}',
  week_of DATE NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cross_creator_niche_hook_week
  ON cross_creator_patterns (niche_id, hook_type, week_of);

CREATE INDEX IF NOT EXISTS idx_cross_creator_week ON cross_creator_patterns (week_of DESC);

ALTER TABLE cross_creator_patterns ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "cross_creator_patterns_select" ON cross_creator_patterns;
CREATE POLICY "cross_creator_patterns_select"
  ON cross_creator_patterns FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "cross_creator_patterns_service" ON cross_creator_patterns;
CREATE POLICY "cross_creator_patterns_service"
  ON cross_creator_patterns FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Called from Cloud Run batch (service_role). Returns aggregates PostgREST cannot express in one query.
CREATE OR REPLACE FUNCTION public.cross_creator_pattern_aggregate (p_lookback_days integer DEFAULT 7)
RETURNS TABLE (
  niche_id integer,
  hook_type text,
  creator_count bigint,
  total_views bigint,
  creators text[]
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    v.niche_id,
    v.hook_type,
    (COUNT(DISTINCT v.creator_handle))::bigint AS creator_count,
    COALESCE(SUM(v.views), 0)::bigint AS total_views,
    COALESCE(
      array_agg(DISTINCT v.creator_handle) FILTER (WHERE v.creator_handle IS NOT NULL),
      ARRAY[]::text[]
    ) AS creators
  FROM video_corpus v
  WHERE
    v.indexed_at > NOW() - make_interval(days => p_lookback_days)
    AND v.hook_type IS NOT NULL
    AND v.creator_handle IS NOT NULL
  GROUP BY v.niche_id, v.hook_type
  HAVING COUNT(DISTINCT v.creator_handle) >= 3
  ORDER BY COALESCE(SUM(v.views), 0) DESC;
$$;

REVOKE ALL ON FUNCTION public.cross_creator_pattern_aggregate (integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cross_creator_pattern_aggregate (integer) TO service_role;
