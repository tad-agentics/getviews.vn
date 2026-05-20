-- Rename legacy "deep_credits" columns to generic credits (V1: one wallet for basic + deep analysis).

ALTER TABLE public.profiles
  RENAME COLUMN deep_credits_remaining TO credits_remaining;

ALTER TABLE public.subscriptions
  RENAME COLUMN deep_credits_granted TO credits_granted;

CREATE OR REPLACE FUNCTION decrement_credit(p_user_id UUID)
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

  UPDATE profiles
  SET
    credits_remaining = credits_remaining - 1,
    lifetime_credits_used = lifetime_credits_used + 1
  WHERE id = p_user_id AND credits_remaining > 0
  RETURNING credits_remaining INTO v_balance;

  RETURN v_balance;
END;
$$;

CREATE OR REPLACE FUNCTION decrement_and_grant_credits(
  p_payos_order_code TEXT,
  p_payos_payment_id TEXT,
  p_event_type TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  sub RECORD;
  v_new_balance INTEGER;
BEGIN
  IF p_event_type <> 'PAID' THEN
    UPDATE subscriptions
    SET status = 'cancelled'
    WHERE payos_order_code = p_payos_order_code AND status = 'pending';

    RETURN jsonb_build_object('ok', true, 'skipped', 'non_paid_event');
  END IF;

  SELECT *
  INTO sub
  FROM subscriptions
  WHERE payos_order_code = p_payos_order_code
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'subscription not found for order %', p_payos_order_code;
  END IF;

  IF sub.status = 'active' THEN
    RETURN jsonb_build_object('ok', true, 'already_active', true);
  END IF;

  UPDATE subscriptions
  SET
    status = 'active',
    payos_payment_id = COALESCE(p_payos_payment_id, payos_payment_id)
  WHERE id = sub.id;

  UPDATE profiles
  SET
    credits_remaining = credits_remaining + sub.credits_granted,
    subscription_tier = sub.tier,
    credits_reset_at = sub.expires_at
  WHERE id = sub.user_id
  RETURNING credits_remaining INTO v_new_balance;

  INSERT INTO credit_transactions (
    user_id,
    delta,
    balance_after,
    reason,
    subscription_id
  )
  VALUES (
    sub.user_id,
    sub.credits_granted,
    v_new_balance,
    'purchase',
    sub.id
  );

  RETURN jsonb_build_object(
    'ok', true,
    'user_id', sub.user_id,
    'new_balance', v_new_balance,
    'tier', sub.tier
  );
END;
$$;
