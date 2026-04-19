-- B.2.1 — KOL reference channels: toggle RPC + raise pin cap (3 → 10).
-- Aligns profiles.reference_channel_handles with phase-b-plan B.0.3 / B.2.

-- Drop legacy cardinality check (was <= 3); replace with <= 10.
DO $$
DECLARE
  con RECORD;
BEGIN
  FOR con IN
    SELECT c.oid, c.conname
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE n.nspname = 'public'
      AND t.relname = 'profiles'
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) ILIKE '%reference_channel_handles%'
  LOOP
    EXECUTE format('ALTER TABLE public.profiles DROP CONSTRAINT %I', con.conname);
  END LOOP;
END $$;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_reference_channel_handles_cap
  CHECK (cardinality(reference_channel_handles) <= 10);

-- Toggle pin: normalized handle append/remove; cap respected on insert.
CREATE OR REPLACE FUNCTION public.toggle_reference_channel(p_handle TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid UUID := auth.uid();
  v_norm TEXT;
  v_cur TEXT[];
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'not_authenticated';
  END IF;

  v_norm := lower(trim(both '@' FROM trim(COALESCE(p_handle, ''))));
  IF v_norm = '' THEN
    RAISE EXCEPTION 'invalid_handle';
  END IF;

  SELECT COALESCE(reference_channel_handles, '{}'::TEXT[])
  INTO v_cur
  FROM profiles
  WHERE id = v_uid
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'profile_not_found';
  END IF;

  IF v_norm = ANY (v_cur) THEN
    UPDATE profiles
    SET reference_channel_handles = array_remove(reference_channel_handles, v_norm)
    WHERE id = v_uid;
  ELSE
    IF cardinality(v_cur) >= 10 THEN
      RETURN;
    END IF;
    UPDATE profiles
    SET reference_channel_handles = array_append(reference_channel_handles, v_norm)
    WHERE id = v_uid;
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.toggle_reference_channel(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.toggle_reference_channel(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.toggle_reference_channel(TEXT) TO service_role;
