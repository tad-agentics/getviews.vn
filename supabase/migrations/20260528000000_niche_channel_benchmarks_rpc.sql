-- 2026-05-28 — RPC: niche_channel_benchmarks(niche_id) for HomeMyChannelSection
--
-- ── Why this exists ─────────────────────────────────────────────────
--
-- The Studio "Tóm tắt kênh" panel (``HomeMyChannelSection``, shipped in
-- the multi-niche Phase) renders 3 percentile bars — View trung bình,
-- Tương tác, Tần suất post — and KPI sub-labels ("Ngách: 89K",
-- "vs ngách 6", "Top 25%: 6+"). The first cut shipped with HEURISTIC
-- placeholders: ``Math.log10(avg + 10) * 14`` for the bar fills and
-- hardcoded "—" / "Top 25%: 6+" for the labels (HomeMyChannelSection.tsx
-- :55-67, :199-219). The structure is right; the data wiring was a TODO.
--
-- This RPC closes that wiring. It returns one row per niche with three
-- aggregate signals:
--
--   - avg_views {median, p75}            → channel-views ranking
--   - engagement_rate {median, p75}      → engagement ranking
--   - posts_per_week {median, p75}       → posting-cadence ranking
--
-- The frontend computes the user's own per-band rank locally
-- (above-p75 → "top 25%", above-p50 → "top 50%", else "top 75%+") and
-- fills the bars with ``user_value / niche_p75`` capped at 100%. That
-- avoids the heavier "compute exact percentile-rank" sub-query while
-- still showing real benchmark data.
--
-- ── Aggregation logic ──────────────────────────────────────────────
--
-- Per-creator aggregates are computed first (CTE), then the niche
-- percentiles are taken across those creator-level values. ``HAVING
-- COUNT(*) >= 3`` excludes one-shot creators whose single video
-- distorts the medians — e.g. a single 5M-view virality wave from an
-- aggregator account. Three is the same threshold ``starter_creators``
-- uses elsewhere.
--
-- Posts/week derives from posted_at MIN/MAX range in the 30d window.
-- For creators whose posts are all in a single day (``MAX - MIN`` < 1
-- week) we floor weeks_active at 1.0 so cadence doesn't go to infinity.
--
-- ── Cost / safety ───────────────────────────────────────────────────
--
-- Read-only. Runs against ``video_corpus`` filtered to one niche +
-- last 30 days. For the largest sampled niche (Tech) this is ~3K rows
-- aggregated to ~150 creators — sub-100ms. RPC is ``STABLE`` so
-- PostgREST caches it appropriately. Permissions: granted to
-- ``authenticated`` (the FE uses the user JWT, not service role) and
-- ``anon`` so the SPA can call it without bouncing through Cloud Run
-- if we ever want to surface it on a marketing landing.
--
-- ── Fallback shape ──────────────────────────────────────────────────
--
-- For a niche with 0 channels meeting the ``HAVING COUNT(*) >= 3``
-- bar, all percentile_cont() values come back NULL. The function
-- coerces those to 0 / 0.0 so the FE can rely on numeric fields and
-- check ``channel_count`` to decide whether to render the bars at
-- all.

CREATE OR REPLACE FUNCTION public.niche_channel_benchmarks(p_niche_id integer)
RETURNS TABLE (
  channel_count       integer,
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
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY avg_views), 0)::integer       AS avg_views_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_views), 0)::integer       AS avg_views_p75,
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY avg_er), 0)::numeric          AS engagement_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_er), 0)::numeric          AS engagement_p75,
    COALESCE(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric  AS posts_per_week_p50,
    COALESCE(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY posts_per_week), 0)::numeric  AS posts_per_week_p75
  FROM per_creator;
$$;

COMMENT ON FUNCTION public.niche_channel_benchmarks(integer) IS
  'Per-niche channel-level percentiles for avg_views, engagement_rate, posts_per_week. Used by /channel/analyze to populate HomeMyChannelSection benchmark labels and bar fills. 30d window, HAVING COUNT(*) >= 3 to exclude one-shot creators.';

GRANT EXECUTE ON FUNCTION public.niche_channel_benchmarks(integer) TO anon, authenticated, service_role;
