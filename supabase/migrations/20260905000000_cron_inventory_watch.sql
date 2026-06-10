-- Cron inventory watch (audit 2026-06-10 hardening).
--
-- Schedules live in the Supabase dashboard (cron.job), not in git — a job
-- silently unscheduled (or deactivated) stalls its pipeline with zero
-- signal. The thumbnail decay shipped exactly this way: the heal endpoint
-- existed, nothing ran it.
--
-- This migration makes the expected inventory explicit in git and asserts
-- it daily, mirroring the pg_net 4xx watch pattern:
--   1. ``expected_cron_jobs`` — the canonical list (UPDATE THIS TABLE in the
--      same migration whenever you cron.schedule/unschedule something).
--   2. ``admin_cron_inventory_drift()`` — RPC for the admin alert evaluator:
--      missing = expected but absent/inactive (severity), unexpected =
--      scheduled but unregistered (informational).
--   3. ``cron_assert_inventory_complete()`` — RAISEs when anything expected
--      is missing/inactive, so cron.job_run_details carries the failure.
--   4. Daily pg_cron ``cron-inventory-watch`` + ``admin_alert_rules`` row.

CREATE TABLE IF NOT EXISTS public.expected_cron_jobs (
  jobname text PRIMARY KEY,
  note text NOT NULL DEFAULT ''
);

ALTER TABLE public.expected_cron_jobs ENABLE ROW LEVEL SECURITY;
-- service-role only; no policies for anon/authenticated.

INSERT INTO public.expected_cron_jobs (jobname, note) VALUES
  ('cron-backfill-classification',      'daily 04:00 — HI-9 classification backfill'),
  ('cron-batch-analytics',              'Sun 21:00 — weekly analytics'),
  ('cron-batch-ingest',                 'daily 20:00 — corpus ingest shift a'),
  ('cron-batch-ingest-shift-b',         'daily 21:30 — corpus ingest shift b'),
  ('cron-batch-ingest-shift-c',         'daily 23:00 — corpus ingest shift c + MV refresh'),
  ('cron-batch-layer0',                 'Sun 21:30 — layer0 weekly'),
  ('cron-batch-morning-ritual',         'daily 15:00 — morning ritual precompute'),
  ('cron-batch-pattern-decks',          'daily 16:00 — pattern decks'),
  ('cron-batch-post-processing',        'daily 23:30 — MV heal if shift c aborts'),
  ('cron-batch-process-ingest-queue',   'daily 01:30 — ingest queue drain'),
  ('cron-batch-r2-janitor',             'Sun 18:00 — R2 orphan prune'),
  ('cron-batch-refresh',                'daily 22:30 — corpus refresh'),
  ('cron-batch-scene-intelligence',     'daily 21:30 — scene intelligence'),
  ('cron-batch-sound-aggregate',        'Mon 21:30 — sound aggregates'),
  ('cron-batch-stats-history-refetch',  'hourly :15 — stats history refetch'),
  ('cron-batch-trend-velocity',         'Mon 22:30 — trend velocity'),
  ('cron-batch-backfill-thumbnails',    'Sun 19:00 — thumbnail self-heal (NULLs + phantom R2)'),
  ('cron-channel-diagnoses-prune',      'Sun 02:15 — channel diagnoses prune'),
  ('cron-daily-health-digest',          'Mon 01:00 — health digest email'),
  ('cron-expiry-check',                 'daily 02:00 — credit pack expiry'),
  ('cron-pg-net-batch-http-4xx-watch',  'hourly :23 — pg_net→batch auth breakage watch'),
  ('cron-prune-webhooks',               'Sun 20:00 — processed_webhook_events prune'),
  ('cron-reset-free-queries',           'daily 17:00 — free quota reset'),
  ('cron-reset-processing',             'every 5 min — TD-3 stuck-lock sweeper'),
  ('cron-starter-creators-reseed',      'Sun 22:45 — starter creators reseed'),
  ('cron-inventory-watch',              'daily 03:30 — this watch itself')
ON CONFLICT (jobname) DO NOTHING;

CREATE OR REPLACE FUNCTION public.admin_cron_inventory_drift()
RETURNS TABLE (jobname text, state text, note text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = cron, public
AS $$
  SELECT e.jobname, 'missing'::text,
         COALESCE(e.note, '') || ' — expected but not scheduled/active'
  FROM public.expected_cron_jobs e
  LEFT JOIN cron.job j ON j.jobname = e.jobname AND j.active
  WHERE j.jobid IS NULL
  UNION ALL
  SELECT j.jobname, 'unexpected'::text,
         'scheduled in dashboard but not registered in expected_cron_jobs'
  FROM cron.job j
  LEFT JOIN public.expected_cron_jobs e ON e.jobname = j.jobname
  WHERE e.jobname IS NULL AND j.active;
$$;

REVOKE ALL ON FUNCTION public.admin_cron_inventory_drift() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_cron_inventory_drift() TO service_role;

COMMENT ON FUNCTION public.admin_cron_inventory_drift() IS
  'Diff between expected_cron_jobs (git-tracked) and live cron.job (dashboard) — admin alert + debugging.';

CREATE OR REPLACE FUNCTION public.cron_assert_inventory_complete()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = cron, public
AS $$
DECLARE
  missing text;
BEGIN
  SELECT string_agg(e.jobname, ', ' ORDER BY e.jobname) INTO missing
  FROM public.expected_cron_jobs e
  LEFT JOIN cron.job j ON j.jobname = e.jobname AND j.active
  WHERE j.jobid IS NULL;

  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'cron inventory drift — expected jobs missing/inactive: %', missing;
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.cron_assert_inventory_complete() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cron_assert_inventory_complete() TO service_role;

SELECT cron.schedule(
  'cron-inventory-watch',
  '30 3 * * *',
  $cmd$SELECT public.cron_assert_inventory_complete()$cmd$
);

INSERT INTO public.admin_alert_rules (rule_key, label, severity, threshold_json)
VALUES (
  'cron_inventory_drift',
  'pg_cron: job kỳ vọng bị thiếu/tắt so với expected_cron_jobs (git)',
  'warn',
  '{"max_missing": 0}'::jsonb
)
ON CONFLICT (rule_key) DO NOTHING;
