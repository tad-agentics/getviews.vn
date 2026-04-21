-- Phase D.2.1 — real body for pattern_wow_diff_7d.
--
-- The C.2.1 stub returned zero rows until a snapshot mechanism existed.
-- Rather than stand up a separate weekly snapshot table, we compute both
-- windows directly from `video_corpus.created_at`:
--
--   current_week = [now - 7d, now)
--   prior_week   = [now - 14d, now - 7d)
--
-- Each window ranks hook_type by video count DESC (ties broken by sum
-- views DESC — heavy-view ties go to the hook with more attention). We
-- keep the top 10 per window; anything outside the top 10 is treated as
-- "not present" so the diff stays stable (a hook sliding from rank 9 to
-- rank 15 in the current week is reported as `is_dropped` from top 10).
--
-- Output shape matches the C.2.1 stub verbatim — the consumer side
-- (`report_pattern.wow_rows_to_wow_diff`) maps to §J `WoWDiff` without
-- changes.

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
  WITH
    now_window AS (
      SELECT
        v.hook_type,
        count(*) AS n_videos,
        COALESCE(sum(v.views), 0) AS sum_views
      FROM public.video_corpus v
      WHERE v.niche_id = p_niche_id
        AND v.hook_type IS NOT NULL
        AND btrim(v.hook_type) <> ''
        AND v.created_at >= now() - INTERVAL '7 days'
      GROUP BY v.hook_type
    ),
    now_ranked AS (
      SELECT hook_type,
             rank() OVER (ORDER BY n_videos DESC, sum_views DESC) AS r
      FROM now_window
    ),
    now_top AS (
      SELECT hook_type, r::INT AS rank_now FROM now_ranked WHERE r <= 10
    ),
    prior_window AS (
      SELECT
        v.hook_type,
        count(*) AS n_videos,
        COALESCE(sum(v.views), 0) AS sum_views
      FROM public.video_corpus v
      WHERE v.niche_id = p_niche_id
        AND v.hook_type IS NOT NULL
        AND btrim(v.hook_type) <> ''
        AND v.created_at >= now() - INTERVAL '14 days'
        AND v.created_at <  now() - INTERVAL '7 days'
      GROUP BY v.hook_type
    ),
    prior_ranked AS (
      SELECT hook_type,
             rank() OVER (ORDER BY n_videos DESC, sum_views DESC) AS r
      FROM prior_window
    ),
    prior_top AS (
      SELECT hook_type, r::INT AS rank_prior FROM prior_ranked WHERE r <= 10
    )
  SELECT
    COALESCE(n.hook_type, p.hook_type) AS hook_type,
    n.rank_now,
    p.rank_prior,
    CASE
      WHEN n.rank_now IS NULL OR p.rank_prior IS NULL THEN NULL
      ELSE (p.rank_prior - n.rank_now)
    END AS rank_change,
    (n.rank_now IS NOT NULL AND p.rank_prior IS NULL) AS is_new,
    (n.rank_now IS NULL AND p.rank_prior IS NOT NULL) AS is_dropped
  FROM now_top n
  FULL OUTER JOIN prior_top p ON p.hook_type = n.hook_type
  ORDER BY COALESCE(n.rank_now, 99), COALESCE(p.rank_prior, 99);
$$;

GRANT EXECUTE ON FUNCTION public.pattern_wow_diff_7d(INT) TO authenticated, service_role;

COMMENT ON FUNCTION public.pattern_wow_diff_7d(INT) IS
  'D.2.1 — real WoW diff over video_corpus.created_at 7d windows. Ranks '
  'hook_type by count DESC (tiebreak sum_views DESC) in the niche. '
  'Top 10 per window; hooks sliding out of top 10 are is_dropped.';
