-- Reconcile remotes where 20260420000046_video_patterns.sql was never applied.
-- Idempotent: safe if video_patterns / pattern_id already exist (matches 46).

CREATE TABLE IF NOT EXISTS public.video_patterns (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signature_hash              TEXT NOT NULL UNIQUE,
  signature                   JSONB NOT NULL,
  display_name                TEXT,
  first_seen_at               TIMESTAMPTZ NOT NULL,
  last_seen_at                TIMESTAMPTZ NOT NULL,
  instance_count              INTEGER NOT NULL DEFAULT 0,
  niche_spread                INTEGER[] NOT NULL DEFAULT '{}',
  weekly_instance_count       INTEGER NOT NULL DEFAULT 0,
  weekly_instance_count_prev  INTEGER NOT NULL DEFAULT 0,
  is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
  computed_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS video_patterns_signature_hash_idx
  ON public.video_patterns (signature_hash);

CREATE INDEX IF NOT EXISTS video_patterns_last_seen_idx
  ON public.video_patterns (last_seen_at DESC);

CREATE INDEX IF NOT EXISTS video_patterns_weekly_delta_idx
  ON public.video_patterns ((weekly_instance_count - weekly_instance_count_prev) DESC);

ALTER TABLE public.video_patterns ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read video_patterns" ON public.video_patterns;
CREATE POLICY "Authenticated users read video_patterns"
  ON public.video_patterns FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS pattern_id UUID REFERENCES public.video_patterns(id);

CREATE INDEX IF NOT EXISTS video_corpus_pattern_id_idx
  ON public.video_corpus (pattern_id)
  WHERE pattern_id IS NOT NULL;
