-- 2026-04-22 templates audit: add ``lifecycle`` to the
-- ``answer_sessions.format`` CHECK constraint.
--
-- Serves three intents previously force-fit into the pattern template:
--   - format_lifecycle_optimize
--   - fatigue
--   - subniche_breakdown
--
-- A follow-up migration in Branch 4 will also add ``diagnostic`` to
-- this constraint for the ``own_flop_no_url`` intent. Keeping these
-- two format literals in separate migrations so each can roll back
-- independently if needed.
--
-- Existing rows are untouched — we're expanding the allowed set, not
-- tightening it, so the ALTER is safe under concurrent writes.

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN ('pattern', 'ideas', 'timing', 'generic', 'lifecycle'));
