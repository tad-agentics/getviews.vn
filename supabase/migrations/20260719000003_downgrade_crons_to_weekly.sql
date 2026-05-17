-- Cron audit follow-up: downgrade three daily jobs to weekly cadence.
--
-- All three jobs were originally scheduled daily but their inputs change
-- weekly or slower. Daily execution is wasted compute + extra batch_job_runs
-- rows that drown signal in the audit logs.
--
-- 1. cron-channel-diagnoses-prune  — channel_diagnoses cache TTL is 7 days
--    (system-design.md §16). Pruning daily means we delete rows that JUST
--    crossed the boundary, so the average pruned row was at most ~12h past
--    expiry. Weekly = at most 7d past expiry — same outcome for storage,
--    1/7th the cron noise.
-- 2. cron-starter-creators-reseed  — starter creators are reseeded from the
--    same EnsembleData hashtag pool the nightly ingest uses. New creators
--    barely change week-over-week for an underexplored niche. Weekly is
--    plenty.
-- 3. cron-daily-health-digest      — was failing silently on auth (Edge
--    Function expected service-role JWT but pg_cron passed it differently;
--    separate fix). At weekly cadence it produces 7x the signal per email
--    and matches Monday-of-the-week mental model when we do flip the auth.

SELECT cron.alter_job(
  job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-channel-diagnoses-prune'),
  schedule := '15 2 * * 0'  -- was '15 2 * * *' (every day 02:15 UTC); now Sundays only
);

SELECT cron.alter_job(
  job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-starter-creators-reseed'),
  schedule := '45 22 * * 0'  -- was '45 22 * * *' (every day 22:45 UTC); now Sundays only
);

SELECT cron.alter_job(
  job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-daily-health-digest'),
  schedule := '0 1 * * 1'  -- was '0 1 * * *' (every day 01:00 UTC); now Mondays only
);

-- Rollback:
--   SELECT cron.alter_job(
--     job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-channel-diagnoses-prune'),
--     schedule := '15 2 * * *'
--   );
--   SELECT cron.alter_job(
--     job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-starter-creators-reseed'),
--     schedule := '45 22 * * *'
--   );
--   SELECT cron.alter_job(
--     job_id := (SELECT jobid FROM cron.job WHERE jobname = 'cron-daily-health-digest'),
--     schedule := '0 1 * * *'
--   );
