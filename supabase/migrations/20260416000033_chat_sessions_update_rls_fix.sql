-- Fix: soft-delete (setting deleted_at) was blocked by PostgREST WITH CHECK.
-- PostgREST re-runs the SELECT policy after UPDATE to verify the row is still
-- visible. The SELECT policy has `deleted_at IS NULL`, so after soft-deleting,
-- the row becomes invisible and PostgREST raises a 403 WITH CHECK violation.
-- Fix: add `deleted_at IS NULL` to USING (only allow updating non-deleted rows)
-- and keep WITH CHECK as `auth.uid() = user_id` only (allows deleted_at to become non-null).
DROP POLICY IF EXISTS "Users update own sessions" ON chat_sessions;

CREATE POLICY "Users update own sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id AND deleted_at IS NULL)
  WITH CHECK (auth.uid() = user_id);
