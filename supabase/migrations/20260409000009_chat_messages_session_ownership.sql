-- Require chat_messages.session_id to belong to the inserting user (session ownership)
DROP POLICY IF EXISTS "chat_messages_insert" ON chat_messages;
DROP POLICY IF EXISTS "users_insert_own_messages" ON chat_messages;
DROP POLICY IF EXISTS "Users insert own messages" ON chat_messages;

CREATE POLICY "chat_messages_insert_own_session"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = user_id
    AND EXISTS (
      SELECT 1
      FROM chat_sessions
      WHERE id = session_id
        AND user_id = auth.uid()
    )
  );
