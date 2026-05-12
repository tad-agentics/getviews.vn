-- Script as Studio Report — allow answer_sessions.format = 'script'.

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN (
    'pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic', 'video', 'script'
  ));
