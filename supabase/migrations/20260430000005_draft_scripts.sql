-- Phase C.8.1 — script_save persistence

CREATE TABLE public.draft_scripts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  niche_id    INTEGER REFERENCES public.niche_taxonomy(id),
  topic       TEXT NOT NULL,
  hook        TEXT NOT NULL,
  hook_delay_ms INTEGER NOT NULL,
  duration_sec INTEGER NOT NULL,
  tone        TEXT NOT NULL,
  shots       JSONB NOT NULL DEFAULT '[]',
  source_session_id UUID REFERENCES public.answer_sessions(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX draft_scripts_user_recent_idx
  ON public.draft_scripts (user_id, updated_at DESC);

ALTER TABLE public.draft_scripts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "draft_scripts_select_own" ON public.draft_scripts
  FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "draft_scripts_modify_own" ON public.draft_scripts
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
