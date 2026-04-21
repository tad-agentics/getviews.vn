-- Phase D.6.6 — admin_action_log.
--
-- Who triggered what on /app/admin, when, with what params, and whether it
-- succeeded. Service-role-only writes + service-role-only reads: the log is
-- for ops accountability, not exposed to end users. The admin dashboard
-- reads it via a Cloud Run endpoint that runs through `require_admin`.
--
-- `params_json` stores the request body (empty object for parameter-less
-- jobs). `result_status` is one of `ok` / `error` — the actual result
-- payload isn't persisted to keep row size bounded; pair with /admin/logs
-- (D.6.4 Cloud Run log tail) for the full output.
--
-- `user_id ON DELETE SET NULL` so a user deletion doesn't wipe the audit
-- trail — the record of the action survives even if the actor's account
-- is removed (matches gemini_calls + chat_archival_audit handling).

CREATE TABLE IF NOT EXISTS public.admin_action_log (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  action         TEXT NOT NULL,
  params_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_status  TEXT NOT NULL,
  error_message  TEXT,
  duration_ms    INTEGER,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT admin_action_log_result_status_valid
    CHECK (result_status IN ('ok', 'error')),
  CONSTRAINT admin_action_log_duration_nonneg
    CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

-- Dashboard group-by: "what has ops been doing this week" + per-action
-- filter for drilling into a single trigger's history.
CREATE INDEX IF NOT EXISTS admin_action_log_action_recent_idx
  ON public.admin_action_log (action, created_at DESC);

-- Per-user view for "what did admin X run today" audit queries.
CREATE INDEX IF NOT EXISTS admin_action_log_user_recent_idx
  ON public.admin_action_log (user_id, created_at DESC)
  WHERE user_id IS NOT NULL;

COMMENT ON TABLE public.admin_action_log IS
  'Phase D.6.6: audit trail for every /app/admin action (trigger POSTs + '
  'reads that matter for ops accountability). service_role insert/select '
  'only; no authenticated grants. Log is fire-and-forget from the Cloud Run '
  'admin handler — a logging failure must not block the admin operation.';

COMMENT ON COLUMN public.admin_action_log.action IS
  'Free-form canonical action string. Examples: "trigger.ingest", '
  '"trigger.morning_ritual", "trigger.analytics", "trigger.scene_intelligence". '
  'Prefix with `trigger.` / `read.` / `mutation.` so action dashboards can '
  'group by category.';

COMMENT ON COLUMN public.admin_action_log.params_json IS
  'Snapshot of the request body (sanitised — no secrets). Empty object for '
  'parameter-less jobs. Trim + cap on the writer side if payloads grow big.';

ALTER TABLE public.admin_action_log ENABLE ROW LEVEL SECURITY;
-- No policies by design. service_role bypasses RLS.
