-- Phase D.1.5 — real 30d view velocity on creator_velocity.
--
-- Background: the frontend shows a "TĂNG 30D" column in /kol (the
-- growth_30d_pct field on each row). Historically this was synthesised
-- client-side by `_growth_display_pct` in kol_browse.py, which re-shapes
-- the niche-wide avg_views percentile into a ±22% band — a proxy, not a
-- real time-series read. We never had follower snapshots to compute
-- real follower growth, so D.1.5 pivots: "view velocity" (recent 30d
-- mean views vs prior 30d mean views, per creator) is the real signal
-- the UI was approximating all along.
--
-- This column is populated by batch_analytics.py Pass 3 (nightly cron
-- via morning_ritual). NULL rows mean "not enough videos in one of the
-- two 30d windows" — kol_browse.py falls back to the avg-views proxy
-- for those creators and emits `[kol-growth]` log lines so the mix of
-- real vs proxy reads is observable when D.5.1 lands the dashboard.
--
-- Follow-up: a `creator_follower_snapshots` table + nightly cron can
-- later replace view-velocity with true follower growth once a 30-day
-- trail exists — that work is queued under D.5.x, not D.1.5.

ALTER TABLE public.creator_velocity
  ADD COLUMN IF NOT EXISTS view_velocity_30d_pct NUMERIC,
  ADD COLUMN IF NOT EXISTS view_velocity_computed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.creator_velocity.view_velocity_30d_pct IS
  'Recent-30d mean views vs prior-30d mean views, as a fraction (0.22 = +22%). NULL when < 2 videos in either window. Populated by batch_analytics Pass 3.';

COMMENT ON COLUMN public.creator_velocity.view_velocity_computed_at IS
  'Timestamp of the last successful view-velocity recompute. kol_browse.py treats rows older than 7d as stale and falls back to the avg-views proxy.';
