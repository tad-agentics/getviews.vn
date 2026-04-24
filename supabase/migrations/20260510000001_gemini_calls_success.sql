-- 2026-05-10 — gemini_calls: add success + error_code columns.
--
-- Axis 5 observability gap: today gemini_calls rows are only inserted
-- on SUCCESS (after generate_content returns), so a Gemini outage or
-- persistent model-rollout bug is invisible in the cost dashboard —
-- you see fewer rows, not explicit failures. This mirrors what
-- batch_job_runs solved for the /batch/* endpoints.
--
-- Columns:
--   success      — true for the existing happy-path rows (default
--                  preserves back-compat for everything shipped
--                  before this migration). Set to false by the
--                  failure writer introduced in the same PR.
--   error_code   — short exception type name (e.g. 'ClientError',
--                  'ServerError', 'DeadlineExceeded', 'ResourceExhausted').
--                  Nullable; only set on success=false rows.
--
-- Existing rows = all historical happy-path calls, so keeping DEFAULT
-- true for back-compat avoids a backfill pass.
--
-- Writer: cloud-run/getviews_pipeline/gemini_cost.py (log_gemini_call +
-- new log_gemini_failure), wired into cloud-run/getviews_pipeline/
-- gemini.py exhausted-retry exception path.

ALTER TABLE public.gemini_calls
  ADD COLUMN IF NOT EXISTS success     BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS error_code  TEXT;

-- Failure-rate dashboard lookup: "which call_site is failing most
-- right now?" needs a partial index on success=false rows.
CREATE INDEX IF NOT EXISTS gemini_calls_failures_recent_idx
  ON public.gemini_calls (call_site, created_at DESC)
  WHERE success = false;

COMMENT ON COLUMN public.gemini_calls.success IS
  'true on happy-path rows (existing behavior). false on rows logged '
  'from gemini.py exhausted-retry failure path. Default true preserves '
  'back-compat for existing rows.';

COMMENT ON COLUMN public.gemini_calls.error_code IS
  'Short exception type name. NULL on success=true rows. Typical values: '
  'ClientError, ServerError, ResourceExhausted, DeadlineExceeded.';
