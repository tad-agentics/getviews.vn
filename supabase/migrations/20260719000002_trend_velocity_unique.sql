-- trend_velocity: add UNIQUE(niche_id, week_start) so on_conflict upsert works.
--
-- Bug: cron-batch-trend-velocity (Tuesday 05:30 ICT) has been silently
-- failing every week since the table was created. Endpoint returns
-- HTTP 200 with body {"ok":false, "errors":["upsert: ... no unique or
-- exclusion constraint matching the ON CONFLICT specification"]}.
-- Result: trend_velocity has 0 rows total (n_tup_ins=0), so the L2.2
-- Sound Radar feature in pattern reports / morning ritual never gets
-- accelerating/peaking/cooling sound buckets.
--
-- Python upsert in cloud-run/getviews_pipeline/trend_velocity.py:329
-- uses on_conflict='niche_id,week_start' which requires a UNIQUE
-- constraint on those two columns. Original table migration was
-- missing it.

ALTER TABLE public.trend_velocity
  ADD CONSTRAINT trend_velocity_niche_week_unique UNIQUE (niche_id, week_start);

-- Rollback:
--   ALTER TABLE public.trend_velocity DROP CONSTRAINT trend_velocity_niche_week_unique;
