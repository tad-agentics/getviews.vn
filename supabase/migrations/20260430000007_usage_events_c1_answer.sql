-- Phase C.1.4 — document + index C.1 `/answer` measurement events (logUsage allow-list in product docs).
-- Table remains free-form TEXT `action`; this migration adds a partial index for dashboards.

COMMENT ON TABLE public.usage_events IS
  'Product analytics (SPA logUsage). B.1: video_screen_load, flop_cta_click, … '
  'C.1 /answer: answer_session_create, answer_turn_append, templatize_click, answer_drawer_open; '
  'C.6: history_session_open; see src/lib/logUsage.ts.';

CREATE INDEX IF NOT EXISTS idx_usage_events_c1_answer
  ON public.usage_events (action, created_at DESC)
  WHERE action IN (
    'answer_session_create',
    'answer_turn_append',
    'templatize_click',
    'answer_drawer_open'
  );
