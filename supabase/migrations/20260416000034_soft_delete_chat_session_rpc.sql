-- PostgREST re-runs the SELECT policy after a PATCH to return the updated row.
-- The SELECT policy has `deleted_at IS NULL`, so after soft-deleting, the row
-- is invisible and PostgREST raises a 403 WITH CHECK violation.
-- Fix: use a SECURITY DEFINER RPC that bypasses PostgREST's post-UPDATE SELECT.
-- The function still enforces ownership (auth.uid() = user_id) and only
-- soft-deletes rows that are not already deleted.

CREATE OR REPLACE FUNCTION soft_delete_chat_session(p_session_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE chat_sessions
  SET deleted_at = now()
  WHERE id = p_session_id
    AND user_id = auth.uid()
    AND deleted_at IS NULL;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Session not found or not owned by user';
  END IF;
END;
$$;
