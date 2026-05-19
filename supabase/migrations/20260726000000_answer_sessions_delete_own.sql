-- Allow authenticated users to hard-delete their own answer_sessions rows.
-- Primary path is Cloud Run ``DELETE /answer/sessions/:id`` (service role);
-- this policy supports direct Supabase client deletes if we wire them later.

CREATE POLICY "answer_sessions_delete_own"
  ON public.answer_sessions FOR DELETE TO authenticated
  USING ((select auth.uid()) = user_id);
