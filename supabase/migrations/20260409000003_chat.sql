-- chat_sessions + chat_messages

CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  title TEXT,
  first_message TEXT NOT NULL,
  intent_type TEXT CHECK (
    intent_type IS NULL OR intent_type IN (
      'video_diagnosis',
      'content_directions',
      'competitor_profile',
      'soi_kenh',
      'brief_generation',
      'trend_spike',
      'find_creators',
      'follow_up',
      'format_lifecycle'
    )
  ),
  credits_used INTEGER NOT NULL DEFAULT 0,
  is_pinned BOOLEAN NOT NULL DEFAULT false,
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX idx_chat_sessions_user_created ON chat_sessions (user_id, created_at DESC);
CREATE INDEX idx_chat_sessions_deleted ON chat_sessions (deleted_at) WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION set_chat_sessions_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_chat_sessions_updated_at
  BEFORE UPDATE ON chat_sessions
  FOR EACH ROW
  EXECUTE PROCEDURE set_chat_sessions_updated_at();

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own non-deleted sessions"
  ON chat_sessions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id AND deleted_at IS NULL);

CREATE POLICY "Users insert own sessions"
  ON chat_sessions FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users cannot delete sessions"
  ON chat_sessions FOR DELETE
  TO authenticated
  USING (false);

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id UUID NOT NULL REFERENCES chat_sessions (id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users (id),
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT,
  intent_type TEXT,
  credits_used INTEGER NOT NULL DEFAULT 0,
  is_free BOOLEAN NOT NULL DEFAULT true,
  structured_output JSONB,
  stream_id TEXT
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages (session_id);
CREATE INDEX idx_chat_messages_user_id ON chat_messages (user_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages (session_id, created_at ASC);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own messages"
  ON chat_messages FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users insert own messages"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Messages are immutable"
  ON chat_messages FOR UPDATE
  TO authenticated
  USING (false);

CREATE POLICY "Messages cannot be deleted directly"
  ON chat_messages FOR DELETE
  TO authenticated
  USING (false);
