-- Switch from soft-delete to real DELETE for chat_sessions.
-- Soft-delete (setting deleted_at) caused PostgREST to re-run the SELECT
-- policy after PATCH, which blocked the update because the row was no longer
-- visible (deleted_at IS NULL policy). Real DELETE avoids this entirely.

-- Remove the old "no delete" policy and add a real DELETE policy.
DROP POLICY IF EXISTS "Users cannot delete sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users update own sessions" ON chat_sessions;

CREATE POLICY "Users delete own sessions"
  ON chat_sessions FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Restore a clean UPDATE policy (for rename/pin use cases, not delete).
CREATE POLICY "Users update own sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Drop the RPC workaround that is no longer needed.
DROP FUNCTION IF EXISTS soft_delete_chat_session(UUID);
