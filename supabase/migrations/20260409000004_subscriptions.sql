-- subscriptions, credit ledger, webhook idempotency + grant RPC

CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  tier TEXT NOT NULL CHECK (tier IN ('starter', 'pro', 'agency')),
  billing_period TEXT NOT NULL
    CHECK (billing_period IN ('monthly', 'biannual', 'annual', 'overage_10', 'overage_30', 'overage_50')),
  amount_vnd INTEGER NOT NULL,
  deep_credits_granted INTEGER NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  payos_order_code TEXT NOT NULL UNIQUE,
  payos_payment_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),
  reminder_7d_sent_at TIMESTAMPTZ,
  reminder_3d_sent_at TIMESTAMPTZ,
  reminder_1d_sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions (user_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_payos_order ON subscriptions (payos_order_code);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own subscriptions"
  ON subscriptions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "No client writes on subscriptions"
  ON subscriptions FOR INSERT
  TO authenticated
  WITH CHECK (false);

CREATE POLICY "No client updates on subscriptions"
  ON subscriptions FOR UPDATE
  TO authenticated
  USING (false);

CREATE POLICY "No client deletes on subscriptions"
  ON subscriptions FOR DELETE
  TO authenticated
  USING (false);

CREATE TABLE IF NOT EXISTS credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  delta INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  reason TEXT NOT NULL CHECK (reason IN ('purchase', 'query', 'refund', 'admin_grant', 'expiry_reset')),
  session_id UUID REFERENCES chat_sessions (id) ON DELETE SET NULL,
  subscription_id UUID REFERENCES subscriptions (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created ON credit_transactions (user_id, created_at DESC);

ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own credit transactions"
  ON credit_transactions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "No client inserts credit transactions"
  ON credit_transactions FOR INSERT
  TO authenticated
  WITH CHECK (false);

CREATE POLICY "No client updates credit transactions"
  ON credit_transactions FOR UPDATE
  TO authenticated
  USING (false);

CREATE POLICY "No client deletes credit transactions"
  ON credit_transactions FOR DELETE
  TO authenticated
  USING (false);

CREATE TABLE IF NOT EXISTS processed_webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payos_order_code TEXT NOT NULL,
  event_type TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_processed_events_order_event
  ON processed_webhook_events (payos_order_code, event_type);

ALTER TABLE processed_webhook_events ENABLE ROW LEVEL SECURITY;

-- No policies: only service_role (bypass) can access

-- Idempotency contract for the PayOS webhook (see TD-2).
--
-- This RPC is **self-idempotent** — it can be called any number of
-- times for the same ``p_payos_order_code`` without granting credits
-- twice. Two mechanisms:
--
--   1. ``SELECT * FROM subscriptions WHERE payos_order_code = ?
--      FOR UPDATE`` row-locks the subscription so concurrent calls
--      serialise.
--   2. After acquiring the lock, ``IF sub.status = 'active'`` bails
--      out with ``already_active: true`` — the row is only updated
--      while it is still ``pending``.
--
-- The webhook handler (``supabase/functions/payos-webhook/
-- index.ts``) calls this RPC FIRST and then inserts the
-- ``processed_webhook_events`` marker. That ordering means a
-- partial-failure mid-call leaves the system in a state the next
-- retry can recover from: the RPC will either no-op (already
-- granted) or grant cleanly (still pending). The ``insert →
-- RPC`` ordering used previously could create a permanently
-- un-granted state when the marker insert committed but the RPC
-- died before completing.
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
    deep_credits_remaining = deep_credits_remaining + sub.deep_credits_granted,
    subscription_tier = sub.tier,
    credits_reset_at = sub.expires_at
  WHERE id = sub.user_id
  RETURNING deep_credits_remaining INTO v_new_balance;

  INSERT INTO credit_transactions (
    user_id,
    delta,
    balance_after,
    reason,
    subscription_id
  )
  VALUES (
    sub.user_id,
    sub.deep_credits_granted,
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

REVOKE ALL ON FUNCTION decrement_and_grant_credits(TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrement_and_grant_credits(TEXT, TEXT, TEXT) TO service_role;
