-- Phase 1.2 — Postgres-backed idempotency for POST /answer/sessions
--
-- Replaces the in-process _IDEMPOTENCY dict in answer_session.py which is
-- unsafe on horizontally-scaled Cloud Run (multiple instances = duplicate rows).
--
-- Design:
--   PRIMARY KEY (user_id, idempotency_key) enforces uniqueness database-side.
--   INSERT ... ON CONFLICT DO NOTHING + SELECT replays the existing session_id.
--   ON DELETE CASCADE keeps the table clean when sessions are hard-deleted.
--   Created_at index supports the daily janitor query (delete rows > 24h old).
--   RLS: enabled with no client-accessible policies — service role only.

CREATE TABLE IF NOT EXISTS public.answer_session_idempotency (
  user_id        uuid        NOT NULL,
  idempotency_key text       NOT NULL,
  session_id     uuid        NOT NULL
    REFERENCES public.answer_sessions(id) ON DELETE CASCADE,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, idempotency_key)
);

ALTER TABLE public.answer_session_idempotency ENABLE ROW LEVEL SECURITY;

-- Index to support janitor: DELETE ... WHERE created_at < now() - interval '24h'
CREATE INDEX IF NOT EXISTS answer_session_idempotency_created_at_idx
  ON public.answer_session_idempotency (created_at);

-- No client RLS policies — service role bypasses RLS.
-- This table is server-internal; no anon/authenticated read/write needed.
