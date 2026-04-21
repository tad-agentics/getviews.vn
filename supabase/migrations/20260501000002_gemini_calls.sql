-- Phase D.5.1 — `gemini_calls` cost table.
--
-- Purpose: daily token spend per call site (pattern_narrative, intent_classifier,
-- video_extraction, …). Inserted async by the `getviews_pipeline.gemini` helper
-- on every `generate_content` success; powers the analytics dashboard panels
-- (daily spend / top-10 spendiest sessions / token-cost ratio trend).
--
-- Scope: service_role inserts only. `authenticated` role has no grant — the
-- wrapper uses a service-role Supabase client. This keeps per-user cost data
-- off the user-client bundle and off the anon-key surface entirely.
--
-- `user_id` nullable + `ON DELETE SET NULL` so the row survives user deletion
-- for aggregate reporting (matches `usage_events` handling).

CREATE TABLE IF NOT EXISTS public.gemini_calls (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  call_site    TEXT NOT NULL,
  model_name   TEXT NOT NULL,
  tokens_in    INTEGER NOT NULL,
  tokens_out   INTEGER NOT NULL,
  cost_usd     NUMERIC(10, 6) NOT NULL,
  duration_ms  INTEGER NOT NULL,
  session_id   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT gemini_calls_tokens_in_nonneg  CHECK (tokens_in  >= 0),
  CONSTRAINT gemini_calls_tokens_out_nonneg CHECK (tokens_out >= 0),
  CONSTRAINT gemini_calls_cost_nonneg       CHECK (cost_usd   >= 0),
  CONSTRAINT gemini_calls_duration_nonneg   CHECK (duration_ms >= 0)
);

-- Dashboard group-by: daily stacked bar of spend by call_site.
CREATE INDEX IF NOT EXISTS gemini_calls_call_site_recent_idx
  ON public.gemini_calls (call_site, created_at DESC);

-- Top-spendiest-sessions panel: keyed on session_id when present.
CREATE INDEX IF NOT EXISTS gemini_calls_session_recent_idx
  ON public.gemini_calls (session_id, created_at DESC)
  WHERE session_id IS NOT NULL;

COMMENT ON TABLE public.gemini_calls IS
  'Phase D.5.1 Gemini token-spend audit. service_role insert only; readers are '
  'analytics dashboards via service_role. One row per successful generate_content '
  'call. call_site identifies the originating helper (pattern_narrative, '
  'intent_classifier, video_extraction, carousel_extraction, ideas_synthesis, …).';

COMMENT ON COLUMN public.gemini_calls.call_site IS
  'Free-form string — must match the `call_site` param passed to '
  '`getviews_pipeline.gemini._generate_content_models`. Grep the pipeline '
  'tree for canonical values.';

COMMENT ON COLUMN public.gemini_calls.session_id IS
  'Optional; set when the call originated from an answer_turn or chat_session '
  'flow, null for batch/cron callers (corpus ingest, niche intelligence).';

ALTER TABLE public.gemini_calls ENABLE ROW LEVEL SECURITY;

-- No authenticated-role policies by design. service_role bypasses RLS and is
-- the only writer. If the analytics dashboard ever moves to authenticated
-- reads, add a SELECT policy scoped to admin user_ids at that point.
