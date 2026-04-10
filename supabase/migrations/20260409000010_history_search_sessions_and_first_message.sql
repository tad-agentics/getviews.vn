-- History: session search RPC + auto-set first_message from first user message

ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS first_message TEXT;

-- ILIKE MVP search; p_user_id must match JWT (SECURITY DEFINER bypasses RLS)
CREATE OR REPLACE FUNCTION public.search_sessions(search_query TEXT, p_user_id UUID)
RETURNS SETOF chat_sessions
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT *
  FROM chat_sessions
  WHERE user_id = p_user_id
    AND p_user_id = auth.uid()
    AND deleted_at IS NULL
    AND (
      first_message ILIKE '%' || search_query || '%'
      OR COALESCE(title, '') ILIKE '%' || search_query || '%'
    )
  ORDER BY created_at DESC
  LIMIT 50;
$$;

REVOKE ALL ON FUNCTION public.search_sessions(TEXT, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.search_sessions(TEXT, UUID) TO authenticated;

CREATE OR REPLACE FUNCTION public.set_session_first_message_from_user_message()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.role = 'user'
     AND NEW.content IS NOT NULL
     AND length(trim(NEW.content)) > 0 THEN
    UPDATE chat_sessions
    SET first_message = NEW.content
    WHERE id = NEW.session_id
      AND (first_message IS NULL OR btrim(first_message) = '');
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_session_first_message ON chat_messages;

CREATE TRIGGER trg_set_session_first_message
  AFTER INSERT ON chat_messages
  FOR EACH ROW
  WHEN (NEW.role = 'user')
  EXECUTE PROCEDURE public.set_session_first_message_from_user_message();
