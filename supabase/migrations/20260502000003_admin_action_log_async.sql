-- Phase D.6.8 — extend admin_action_log for async job tracking.
--
-- D.6.6 shipped admin_action_log as an append-only audit written
-- *after* the trigger ran. For jobs that take > 60s (corpus ingest
-- across all niches, morning-ritual, analytics), the synchronous
-- request times out from the client side even though the server keeps
-- working. This migration lets the same row transition through
-- queued → running → ok / error so the SPA can poll a single ID
-- without needing a second table.
--
-- Changes:
--   1. CHECK constraint expanded: {ok, error} → {queued, running, ok, error}.
--   2. result_json column added (nullable JSONB) so the polled response
--      can carry the real output, not just a status string.
--
-- No backfill needed — existing rows are all in terminal ok/error state;
-- the constraint swap is a superset.

ALTER TABLE public.admin_action_log
  DROP CONSTRAINT IF EXISTS admin_action_log_result_status_valid;

ALTER TABLE public.admin_action_log
  ADD CONSTRAINT admin_action_log_result_status_valid
    CHECK (result_status IN ('queued', 'running', 'ok', 'error'));

ALTER TABLE public.admin_action_log
  ADD COLUMN IF NOT EXISTS result_json JSONB;

COMMENT ON COLUMN public.admin_action_log.result_status IS
  'Job lifecycle: queued (row inserted, task not yet picked up) → '
  'running (task executing) → ok / error (terminal). The SPA polls a '
  'single row through this state machine.';

COMMENT ON COLUMN public.admin_action_log.result_json IS
  'Captured response payload from the underlying runner (e.g. '
  'corpus_ingest summary). Populated on the terminal transition. Kept '
  'JSONB so ad-hoc ops queries (avg inserted_count, failure pattern, '
  'etc.) stay queryable without a separate results table.';
