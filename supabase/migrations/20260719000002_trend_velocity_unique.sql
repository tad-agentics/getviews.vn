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

-- Idempotent: the constraint was applied out-of-band via apply_migration on
-- 2026-05-17 (commit 468eab6) before this file was registered in
-- supabase_migrations.schema_migrations, so ``supabase db push`` will replay
-- this file against a DB that already has the constraint. ``ALTER TABLE ...
-- ADD CONSTRAINT`` has no ``IF NOT EXISTS`` clause in Postgres, hence the
-- DO block with a duplicate_object catch.
DO $$
BEGIN
  ALTER TABLE public.trend_velocity
    ADD CONSTRAINT trend_velocity_niche_week_unique UNIQUE (niche_id, week_start);
EXCEPTION
  WHEN duplicate_object THEN
    RAISE NOTICE 'trend_velocity_niche_week_unique already exists — skipping';
  WHEN duplicate_table THEN
    -- Some Postgres versions raise duplicate_table for constraint conflicts.
    RAISE NOTICE 'trend_velocity_niche_week_unique already exists — skipping';
END
$$;

-- Rollback:
--   ALTER TABLE public.trend_velocity DROP CONSTRAINT trend_velocity_niche_week_unique;
