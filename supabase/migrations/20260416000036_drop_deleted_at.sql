-- Clean up soft-delete remnants now that real DELETE is in place.
-- Drop policies referencing deleted_at, recreate them cleanly, then drop the column.

DROP POLICY IF EXISTS "Users read own non-deleted sessions" ON chat_sessions;
CREATE POLICY "Users read own sessions"
  ON chat_sessions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own sessions" ON chat_sessions;
CREATE POLICY "Users update own sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

ALTER TABLE chat_sessions DROP COLUMN deleted_at;
