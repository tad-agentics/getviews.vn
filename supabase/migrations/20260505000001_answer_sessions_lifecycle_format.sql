-- 2026-04-22 templates audit: ``answer_sessions.format`` CHECK constraint.
-- Originally added only ``lifecycle``; constraint text now matches the
-- union of lifecycle + diagnostic + video so greenfield / out-of-order
-- applies never tighten the check below existing row values.
--
-- Must not narrow the allowed set: duplicate historical timestamps meant
-- some databases already had ``diagnostic`` / ``video`` (see
-- ``20260428000000_answer_sessions_video_format``) before this version
-- applied. Re-applying a subset would violate existing rows (23514).

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN (
    'pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic', 'video'
  ));
