-- Close batch_job_runs rows stuck in status='running' after Cloud Run's 3600s
-- hard kill (shift B/C ingest orphans). Mirrors sweep_stale_running_job_runs
-- in cloud-run/getviews_pipeline/batch_observability.py.

CREATE OR REPLACE FUNCTION public.sweep_stale_batch_job_runs(stale_minutes int DEFAULT 65)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  swept int := 0;
BEGIN
  WITH stale AS (
    SELECT id, summary, started_at
    FROM public.batch_job_runs
    WHERE status = 'running'
      AND started_at < now() - make_interval(mins => stale_minutes)
  ),
  updated AS (
    UPDATE public.batch_job_runs b
    SET
      status = 'failed',
      finished_at = now(),
      duration_ms = GREATEST(
        0,
        (EXTRACT(EPOCH FROM (now() - b.started_at)) * 1000)::int
      ),
      error = left(
        format(
          'auto-swept: still running >%s m (likely Cloud Run 3600s timeout orphan)',
          stale_minutes
        ),
        5000
      ),
      summary = COALESCE(b.summary, '{}'::jsonb) || jsonb_build_object(
        'aborted_early', true,
        'swept_stale_running', true
      )
    FROM stale s
    WHERE b.id = s.id
    RETURNING b.id
  )
  SELECT count(*)::int INTO swept FROM updated;

  RETURN swept;
END;
$$;

REVOKE ALL ON FUNCTION public.sweep_stale_batch_job_runs(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.sweep_stale_batch_job_runs(int) TO service_role;

COMMENT ON FUNCTION public.sweep_stale_batch_job_runs(int) IS
  'Mark batch_job_runs stuck running past stale_minutes as failed (Cloud Run timeout orphans).';

SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname = 'cron-batch-job-runs-stale-sweeper';

SELECT cron.schedule(
  'cron-batch-job-runs-stale-sweeper',
  '*/15 * * * *',
  $cmd$SELECT public.sweep_stale_batch_job_runs(65)$cmd$
);

INSERT INTO public.expected_cron_jobs (jobname, note) VALUES
  ('cron-batch-job-runs-stale-sweeper', 'every 15m — close batch_job_runs running >65m')
ON CONFLICT (jobname) DO UPDATE SET note = EXCLUDED.note;

UPDATE public.expected_cron_jobs
SET note = 'daily 23:00 — corpus ingest shift c (no inline MV; cron-batch-post-processing heals)'
WHERE jobname = 'cron-batch-ingest-shift-c';
