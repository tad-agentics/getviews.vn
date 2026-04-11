-- §13 abuse gate: atomic increment of daily_free_query_count
-- Returns the new count so caller can check against the daily limit.
-- Security definer so the function can update profiles for authenticated users.

CREATE OR REPLACE FUNCTION increment_free_query_count(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_count INTEGER;
BEGIN
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

-- Remove public access; only authenticated users may call this.
REVOKE ALL ON FUNCTION increment_free_query_count(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION increment_free_query_count(UUID) TO authenticated;
