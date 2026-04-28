-- 2026-04-28 — add ``video`` to the ``answer_sessions.format`` CHECK constraint.
--
-- Serves the ``video_diagnosis`` intent, which is being migrated from a
-- standalone ``/app/video`` screen to a template body inside the
-- ``/app/answer`` research surface. Mirrors the lifecycle (20260505) +
-- diagnostic (20260506) format additions — same rationale: each
-- structured report becomes a session format so the answer surface is
-- the single home for analytical output.
--
-- This migration ships dark — no /stream emit logic, no FE dispatch,
-- no inbound routing yet. It just expands the allowed set so PR-2 can
-- start writing rows with format='video' without violating the check.
-- Existing rows are untouched.

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN (
    'pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic', 'video'
  ));
