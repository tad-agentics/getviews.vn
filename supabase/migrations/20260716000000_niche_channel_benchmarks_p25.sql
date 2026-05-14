-- Add 25th percentile for avg_views to niche_channel_benchmarks (channel diagnosis score card).

CREATE OR REPLACE FUNCTION public.niche_channel_benchmarks(p_niche_id integer)
RETURNS TABLE (
  channel_count       integer,
  avg_views_p25       integer,
  avg_views_p50       integer,
  avg_views_p75       integer,
  engagement_p50      numeric,
  engagement_p75      numeric,
  posts_per_week_p50  numeric,
  posts_per_week_p75  numeric
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  WITH per_creator AS (
    SELECT
      creator_handle,
      AVG(views)::float                 AS avg_views,
      AVG(engagement_rate)::float       AS avg_er,
      (COUNT(*)::float
         / GREATEST(
             EXTRACT(EPOCH FROM (MAX(posted_at) - MIN(posted_at))) / 604800.0,
             1.0
           ))                            AS posts_per_week
    FROM video_corpus
    WHERE niche_id = p_niche_id
      AND posted_at IS NOT NULL
      AND posted_at > NOW() - INTERVAL '30 days'
      AND creator_handle IS NOT NULL
    GROUP BY creator_handle
    HAVING COUNT(*) >= 3
  )
  SELECT
    COUNT(*)::integer                                                    AS channel_count,
    COALESCE(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_views), 0)::integer       AS avg_views_p25,
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY avg_views), 0)::integer       AS avg_views_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_views), 0)::integer       AS avg_views_p75,
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY avg_er), 0)::numeric          AS engagement_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_er), 0)::numeric          AS engagement_p75,
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric  AS posts_per_week_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric  AS posts_per_week_p75
  FROM per_creator;
$$;

COMMENT ON FUNCTION public.niche_channel_benchmarks(integer) IS
  'Per-niche channel-level percentiles for avg_views (p25/p50/p75), engagement_rate, posts_per_week. 30d window, HAVING COUNT(*) >= 3. Used by channel diagnosis score card + HomeMyChannelSection.';

GRANT EXECUTE ON FUNCTION public.niche_channel_benchmarks(integer) TO anon, authenticated, service_role;
