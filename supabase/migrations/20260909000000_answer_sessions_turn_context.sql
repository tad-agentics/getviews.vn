-- AQ-9 — Add turn_context JSONB to answer_sessions so follow-up turns can
-- access top_hook_types + evidence_video_ids from the primary turn without
-- an extra query.  Written by Cloud Run (service role) immediately after the
-- primary turn payload is validated and stored.  RLS: no direct client
-- read/write needed — Cloud Run owns both the write (service role) and the
-- follow-up read.

ALTER TABLE public.answer_sessions
  ADD COLUMN IF NOT EXISTS turn_context JSONB;

COMMENT ON COLUMN public.answer_sessions.turn_context IS
  'Populated after primary turn: {top_hook_types: str[], evidence_video_ids: str[]}. '
  'Used by follow-up builder dispatch in answer_session.py to surface relevant hooks '
  'and reference videos from the primary analysis.';
