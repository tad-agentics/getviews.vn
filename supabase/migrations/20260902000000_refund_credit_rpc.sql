-- TD-1 completion: compensating refund when a paid pipeline fails AFTER
-- decrement_credit succeeded (Gemini 429, builder crash, channel diagnose
-- task failure). Until now every post-deduct failure silently kept the
-- user's credits — see audit 2026-06-10 finding C-1.
--
-- SECURITY: unlike decrement_credit (callable by the authenticated user,
-- safe because it only subtracts), refund_credit MINTS credits and must
-- never be callable from the client — service_role only. Cloud Run calls
-- it via the service client on failure paths.

CREATE OR REPLACE FUNCTION public.refund_credit(p_user_id UUID, p_amount INT)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_balance INTEGER;
BEGIN
  IF p_amount IS NULL OR p_amount < 1 THEN
    RAISE EXCEPTION 'invalid amount' USING ERRCODE = '22023';
  END IF;

  UPDATE profiles
  SET
    credits_remaining = credits_remaining + p_amount,
    lifetime_credits_used = GREATEST(lifetime_credits_used - p_amount, 0)
  WHERE id = p_user_id
  RETURNING credits_remaining INTO v_balance;

  IF v_balance IS NULL THEN
    RETURN NULL; -- unknown user; caller logs, nothing to compensate
  END IF;

  -- Audit trail so support can answer "where did this credit come from".
  INSERT INTO credit_transactions (user_id, delta, balance_after, reason)
  VALUES (p_user_id, p_amount, v_balance, 'refund');

  RETURN v_balance;
END;
$$;

REVOKE ALL ON FUNCTION public.refund_credit(UUID, INT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.refund_credit(UUID, INT) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.refund_credit(UUID, INT) TO service_role;
