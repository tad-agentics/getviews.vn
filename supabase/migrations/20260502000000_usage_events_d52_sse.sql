-- Phase D.5.2 — SSE drop-rate observability events.
--
-- `useSessionStream` (client-side) now emits three new action strings on the
-- answer_turn SSE flow. This migration documents them and adds a partial
-- index so the cost/quality dashboard can filter on them without scanning
-- the full usage_events table.
--
-- Wire-protocol events:
--   sse_drop             — SSE reader hit unexpected EOF without a done token,
--                          or fetch returned non-2xx. metadata keys:
--                          { endpoint, session_id?, last_seq, reason }.
--                          reason ∈ {network|abort|server|unknown}.
--   sse_resume_attempt   — Client retried with ?resume_stream_id=&resume_from_seq=
--                          metadata keys: { endpoint, session_id?, attempted_seq,
--                                           cross_pod_likely }.
--   sse_resume_success   — Payload received on the retry attempt.
--                          metadata keys: { endpoint, session_id? }.
--
-- See src/hooks/useSessionStream.ts for the emit sites.

COMMENT ON TABLE public.usage_events IS
  'Product analytics (SPA logUsage + server emit). B.1: video_screen_load, '
  'flop_cta_click, script_screen_load, script_generate. '
  'C.1 /answer: answer_session_create, answer_turn_append, templatize_click, '
  'answer_drawer_open. '
  'C.6: history_session_open. '
  'D.1.1: script_save. '
  'D.2.3 server-emit: classifier_low_confidence, pattern_what_stalled_empty. '
  'D.5.2 SSE: sse_drop, sse_resume_attempt, sse_resume_success. '
  'See src/lib/logUsage.ts + src/hooks/useSessionStream.ts + '
  'cloud-run/getviews_pipeline/answer_session.py.';

CREATE INDEX IF NOT EXISTS idx_usage_events_d52_sse
  ON public.usage_events (action, created_at DESC)
  WHERE action IN (
    'sse_drop',
    'sse_resume_attempt',
    'sse_resume_success'
  );
