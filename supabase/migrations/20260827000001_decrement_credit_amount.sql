-- TD-1: atomic multi-credit deduction (Wave 3 deep = 2×, script = 3×) — no partial charge on failure.

DROP FUNCTION IF EXISTS public.decrement_credit(uuid);

CREATE OR REPLACE FUNCTION decrement_credit(p_user_id UUID, p_amount INT DEFAULT 1)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_balance INTEGER;
BEGIN
  IF auth.uid() IS NULL OR p_user_id <> auth.uid() THEN
    RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
  END IF;

  IF p_amount IS NULL OR p_amount < 1 THEN
    RAISE EXCEPTION 'invalid amount' USING ERRCODE = '22023';
  END IF;

  UPDATE profiles
  SET
    credits_remaining = credits_remaining - p_amount,
    lifetime_credits_used = lifetime_credits_used + p_amount
  WHERE id = p_user_id AND credits_remaining >= p_amount
  RETURNING credits_remaining INTO v_balance;

  RETURN v_balance;
END;
$$;

REVOKE ALL ON FUNCTION decrement_credit(UUID, INT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrement_credit(UUID, INT) TO authenticated;

ALTER FUNCTION public.decrement_credit(p_user_id uuid, p_amount int)
  SET search_path = public, pg_temp;
