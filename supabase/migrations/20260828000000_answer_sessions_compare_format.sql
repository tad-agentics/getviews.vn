-- Compare as Studio Report — allow answer_sessions.format = 'compare'.
-- Two-URL side-by-side diagnosis migrated off the legacy /stream chat path
-- into a first-class answer-session format (rendered by CompareBody).

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN (
    'pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic', 'video', 'script', 'compare'
  ));
