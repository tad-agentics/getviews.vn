-- Phase D.2.3 — document + index D-era measurement events.
-- `usage_events.action` remains free-form TEXT; this migration adds a
-- partial index so the D.5.1 dashboard can filter by the new D events
-- without scanning the full table.

COMMENT ON TABLE public.usage_events IS
  'Product analytics (SPA logUsage + server emit). B.1: video_screen_load, '
  'flop_cta_click, script_screen_load, script_generate. '
  'C.1 /answer: answer_session_create, answer_turn_append, templatize_click, '
  'answer_drawer_open. '
  'C.6: history_session_open. '
  'D.1.1: script_save. '
  'D.2.3 server-emit: classifier_low_confidence, pattern_what_stalled_empty. '
  'See src/lib/logUsage.ts + cloud-run/getviews_pipeline/answer_session.py.';

CREATE INDEX IF NOT EXISTS idx_usage_events_d2_observability
  ON public.usage_events (action, created_at DESC)
  WHERE action IN (
    'classifier_low_confidence',
    'pattern_what_stalled_empty',
    'script_save'
  );
