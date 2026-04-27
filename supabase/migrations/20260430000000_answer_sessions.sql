-- Phase C.0.5 — answer_sessions + answer_turns (§J payload storage)
-- RLS: users read own rows; payload writes via service role on Cloud Run.

CREATE TABLE IF NOT EXISTS public.answer_sessions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  niche_id     INTEGER REFERENCES public.niche_taxonomy(id),
  title        TEXT NOT NULL,
  initial_q    TEXT NOT NULL,
  intent_type  TEXT NOT NULL,
  format       TEXT NOT NULL CHECK (format IN ('pattern', 'ideas', 'timing', 'generic')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS answer_sessions_user_recent_idx
  ON public.answer_sessions (user_id, updated_at DESC)
  WHERE archived_at IS NULL;

ALTER TABLE public.answer_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "answer_sessions_select_own" ON public.answer_sessions
  FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "answer_sessions_insert_own" ON public.answer_sessions
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "answer_sessions_update_own" ON public.answer_sessions
  FOR UPDATE TO authenticated
  USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS public.answer_turns (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   UUID NOT NULL REFERENCES public.answer_sessions(id) ON DELETE CASCADE,
  turn_index   INTEGER NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('primary', 'timing', 'creators', 'script', 'generic')),
  query        TEXT NOT NULL,
  payload      JSONB NOT NULL DEFAULT '{}',
  classifier_confidence TEXT NOT NULL CHECK (classifier_confidence IN ('high', 'medium', 'low')),
  intent_confidence TEXT NOT NULL CHECK (intent_confidence IN ('high', 'medium', 'low')),
  cloud_run_run_id TEXT,
  credits_used INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS answer_turns_session_order_idx
  ON public.answer_turns (session_id, turn_index);

ALTER TABLE public.answer_turns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "answer_turns_select_own" ON public.answer_turns
  FOR SELECT TO authenticated
  USING (
    auth.uid() = (SELECT user_id FROM public.answer_sessions WHERE id = session_id)
  );

COMMENT ON TABLE public.answer_sessions IS 'Phase C /answer research sessions';
COMMENT ON TABLE public.answer_turns IS 'Append-only turns; payload = ReportV1 JSON (validated server-side)';
