-- 2026-05-08 — tighten ``answer_sessions_update_own`` with a WITH CHECK clause.
--
-- Background: the policy has always been
--
--   CREATE POLICY "answer_sessions_update_own" ON public.answer_sessions
--     FOR UPDATE TO authenticated
--     USING (auth.uid() = user_id);
--
-- USING gates which rows the user can touch (rows they own). Without a
-- WITH CHECK, there's nothing stopping the caller from setting the row's
-- ``user_id`` column to another user's id during UPDATE, effectively
-- handing the row to the victim.
--
-- Not exploited in production today — the only code path that updates
-- ``answer_sessions`` is the ``patch_session`` Cloud Run endpoint, which
-- only touches ``title`` and ``archived_at``. But a malicious user
-- crafting a direct ``PATCH /rest/v1/answer_sessions?id=eq.<their-row>``
-- with ``{"user_id": "<victim>"}`` could abuse the gap.
--
-- Fix: add ``WITH CHECK ((select auth.uid()) = user_id)`` matching the
-- pattern already used on ``profiles_update_own``, ``push_events_
-- update_own_read_state``, and ``competitor_tracking_update_own``. The
-- ``(select auth.uid())`` form preserves the init-plan optimisation
-- applied to the rest of the policies in the 2026-05-04 RLS hardening
-- batch.
--
-- Semantics after this migration:
--   - USING clause (unchanged): user can only UPDATE their own rows.
--   - WITH CHECK clause (new): the post-update row's ``user_id`` must
--     still equal the caller. Attempts to re-assign ownership fail with
--     ``new row violates row-level security policy``.

DROP POLICY IF EXISTS "answer_sessions_update_own" ON public.answer_sessions;

CREATE POLICY "answer_sessions_update_own"
  ON public.answer_sessions FOR UPDATE TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);
