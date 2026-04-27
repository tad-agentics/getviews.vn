-- profiles + handle_new_user + credit RPCs

CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  display_name TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL,
  avatar_url TEXT,
  primary_niche TEXT,
  niche_id INTEGER REFERENCES niche_taxonomy (id),
  tiktok_handle TEXT,
  subscription_tier TEXT NOT NULL DEFAULT 'free'
    CHECK (subscription_tier IN ('free', 'starter', 'pro', 'agency')),
  deep_credits_remaining INTEGER NOT NULL DEFAULT 10
    CHECK (deep_credits_remaining >= 0),
  lifetime_credits_used INTEGER NOT NULL DEFAULT 0,
  credits_reset_at TIMESTAMPTZ,
  daily_free_query_count INTEGER NOT NULL DEFAULT 0,
  daily_free_query_reset_at TIMESTAMPTZ,
  is_processing BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_profiles_niche_id ON profiles (niche_id);

CREATE OR REPLACE FUNCTION set_profiles_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW
  EXECUTE PROCEDURE set_profiles_updated_at();

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- No INSERT/DELETE for clients — handle_new_user trigger creates the row

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name, email, avatar_url)
  VALUES (
    NEW.id,
    COALESCE(
      NEW.raw_user_meta_data->>'full_name',
      NEW.raw_user_meta_data->>'name',
      split_part(COALESCE(NEW.email, 'user'), '@', 1),
      ''
    ),
    COALESCE(NEW.email, ''),
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE PROCEDURE public.handle_new_user();

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
    deep_credits_remaining = deep_credits_remaining - 1,
    lifetime_credits_used = lifetime_credits_used + 1
  WHERE id = p_user_id AND deep_credits_remaining > 0
  RETURNING deep_credits_remaining INTO v_balance;

  RETURN v_balance;
END;
$$;

REVOKE ALL ON FUNCTION decrement_credit(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrement_credit(UUID) TO authenticated;
