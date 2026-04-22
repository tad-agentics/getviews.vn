-- 2026-04-22 templates audit: add ``diagnostic`` to the
-- ``answer_sessions.format`` CHECK constraint.
--
-- Serves the ``own_flop_no_url`` intent (URL-less flop diagnosis)
-- which was previously force-fit into the pattern template. Diagnosis
-- is a different shape from a niche hook leaderboard — 5 fixed
-- failure-mode categories with 4-level verdicts, no numeric score.
--
-- Follows the lifecycle format addition from 20260505000000. Kept as
-- a separate migration so each literal can roll back independently if
-- needed.
--
-- Existing rows are untouched — we're expanding the allowed set, not
-- tightening it, so the ALTER is safe under concurrent writes.

ALTER TABLE public.answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;

ALTER TABLE public.answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN (
    'pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic'
  ));
