-- TD-3 hardening: atomic begin_processing() guard.
--
-- Background. Both api/chat.ts and cloud-run intent.py used to fire an
-- unconditional UPDATE profiles SET is_processing=true at the start of a
-- request. Two concurrent requests from the same user (double-click,
-- duplicate tab, retry) could both pass that line, both deduct a credit,
-- and both spin up a Gemini synthesis. The cron-reset-processing job
-- only clears flags older than 5 min, so the guard was leaky.
--
-- Fix. ``begin_processing(p_user_id)`` performs a single conditional
-- UPDATE that flips the flag only when it was previously false, then
-- returns the prior value. Callers acquire the lock iff the function
-- returns false (was-not-set → now-set), and abort with 409 otherwise.

CREATE OR REPLACE FUNCTION begin_processing(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_already_processing BOOLEAN;
BEGIN
  -- Same caller check as decrement_credit: only the user themselves
  -- (via authenticated JWT) may flip their own processing flag.
  IF auth.uid() IS NULL OR p_user_id <> auth.uid() THEN
    RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
  END IF;

  UPDATE profiles
  SET is_processing = TRUE
  WHERE id = p_user_id AND is_processing = FALSE
  RETURNING FALSE INTO v_already_processing;

  -- v_already_processing is FALSE when the conditional UPDATE matched
  -- (lock acquired). When the row was already locked, the UPDATE
  -- matches zero rows and v_already_processing stays NULL → coerce to
  -- TRUE so callers see the lock as held.
  RETURN COALESCE(v_already_processing, TRUE);
END;
$$;

REVOKE ALL ON FUNCTION begin_processing(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION begin_processing(UUID) TO authenticated;

COMMENT ON FUNCTION begin_processing(UUID) IS
  'Atomic TD-3 lock acquire. Returns FALSE when the lock was just '
  'acquired (caller may proceed); returns TRUE when the row was '
  'already is_processing=TRUE (caller must abort with 409).';
