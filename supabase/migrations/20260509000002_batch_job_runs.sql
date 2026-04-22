-- 2026-05-09 — batch_job_runs: cron observability at the endpoint level.
--
-- Closes the Axis 5 gap surfaced in state-of-corpus.md: today if a
-- data-pipeline cron silently fails (e.g. EnsembleData rate-limit,
-- Gemini 500, Supabase connection flap) we only notice when the
-- downstream tables stop growing. There is no failure surface.
--
-- This table records one row per /batch/* invocation:
--   - INSERT at entry with status='running'
--   - UPDATE on clean exit with status='ok', duration_ms, summary
--   - UPDATE on exception with status='failed', duration_ms, error
--
-- Distinct from the existing ``batch_failures`` table, which is
-- per-video (``video_id NOT NULL``) and intended for ingestion-level
-- row-skipping decisions. ``batch_job_runs`` is per-cron-run —
-- different semantics, different cardinality, different readers.
--
-- Readers (future): admin dashboard freshness widget, alert-rules
-- engine querying for ``status = 'failed'`` in the last 24h.

CREATE TABLE IF NOT EXISTS public.batch_job_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name      TEXT NOT NULL,
  started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at   TIMESTAMPTZ,
  status        TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'ok', 'failed')),
  duration_ms   INTEGER,
  summary       JSONB,
  error         TEXT
);

-- Hot lookup: "last N runs of job X"
CREATE INDEX IF NOT EXISTS batch_job_runs_job_name_started_idx
  ON public.batch_job_runs (job_name, started_at DESC);

-- Alert-engine lookup: "any failed run in the last 24h"
CREATE INDEX IF NOT EXISTS batch_job_runs_failed_idx
  ON public.batch_job_runs (started_at DESC)
  WHERE status = 'failed';

ALTER TABLE public.batch_job_runs ENABLE ROW LEVEL SECURITY;

-- Service role writes (via Cloud Run). No authenticated-role policies
-- today — admin surfaces will route through service-role RPCs as they
-- get built. Keeping the table RLS-locked by default is the safer
-- stance until the admin UX is in place.

COMMENT ON TABLE public.batch_job_runs IS
  'Cron job observability — one row per /batch/* invocation. Written by Cloud Run via service_role. See cloud-run/getviews_pipeline/batch_observability.py.';
