-- chat_messages: no UPDATE/DELETE policies (default deny = immutable)
DROP POLICY IF EXISTS "Messages are immutable" ON chat_messages;
DROP POLICY IF EXISTS "Messages cannot be deleted directly" ON chat_messages;

-- chat_sessions.niche_id for per-session niche (chat-core hooks)
ALTER TABLE chat_sessions
  ADD COLUMN IF NOT EXISTS niche_id INTEGER REFERENCES niche_taxonomy (id);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_niche_id ON chat_sessions (niche_id);
