-- Security: add an ownership guard to increment_free_query_count.
--
-- The SECURITY DEFINER body trusted the client-supplied p_user_id, so any
-- authenticated user could call rpc('increment_free_query_count', {p_user_id:
-- <victim>}) to inflate another user's daily_free_query_count past
-- FREE_DAILY_LIMIT and deny them free queries. Mirror the decrement_credit
-- guard (20260827000001) — auth.uid() must equal p_user_id.
--
-- Caller safety: the sole caller (cloud-run intent.py /stream) invokes this via
-- a user-scoped client (user_supabase(access_token)) passing the caller's own
-- id, so auth.uid() = p_user_id and the guard is transparent there.

CREATE OR REPLACE FUNCTION increment_free_query_count(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_count INTEGER;
BEGIN
  IF auth.uid() IS NULL OR p_user_id <> auth.uid() THEN
    RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
  END IF;

  UPDATE profiles
  SET daily_free_query_count = daily_free_query_count + 1
  WHERE id = p_user_id
  RETURNING daily_free_query_count INTO v_count;

  IF v_count IS NULL THEN
    RAISE EXCEPTION 'User % not found in profiles', p_user_id;
  END IF;

  RETURN jsonb_build_object('new_count', v_count);
END;
$$;

REVOKE ALL ON FUNCTION increment_free_query_count(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION increment_free_query_count(UUID) TO authenticated;
