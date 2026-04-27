-- TD-3 hardening (audit #18): lock down ``profiles.is_processing``.
--
-- ``profiles_update_own`` RLS allows authenticated users to UPDATE
-- any column of their own row, ``is_processing`` included. A user
-- could clear the flag client-side, defeat the TD-3 concurrent-
-- request guard, and trigger duplicate credit deductions on
-- ``/stream`` or ``/api/chat``.
--
-- Postgres has no native column-level RLS, so this migration uses
-- column-level GRANTs to deny non-service-role writes:
--
--   1. REVOKE UPDATE (is_processing) FROM authenticated.
--   2. Add ``end_processing(p_user_id)`` SECURITY DEFINER RPC so
--      the legitimate "I finished my request, clear the flag"
--      path keeps working without giving the authenticated role
--      blanket UPDATE rights on the column.
--
-- Existing writers and what they switch to:
--
--   - ``begin_processing(uuid)`` (this RPC was added in
--     20260607000000) — SECURITY DEFINER, runs as the function
--     owner; column GRANT applies to invoker so the RPC body
--     keeps writing.
--   - ``cron-reset-processing`` Edge Function — uses service_role
--     and bypasses RLS + column GRANTs anyway.
--   - api/chat.ts + cloud-run intent.py — user-scoped clients;
--     they now call ``end_processing`` instead of issuing direct
--     UPDATEs (see same-PR diff).

CREATE OR REPLACE FUNCTION end_processing(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF auth.uid() IS NULL OR p_user_id <> auth.uid() THEN
    RAISE EXCEPTION 'not allowed' USING ERRCODE = '42501';
  END IF;

  UPDATE profiles
  SET is_processing = FALSE
  WHERE id = p_user_id;

  RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION end_processing(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION end_processing(UUID) TO authenticated;

COMMENT ON FUNCTION end_processing(UUID) IS
  'TD-3 lock release. Sets is_processing=FALSE for the calling '
  'user via SECURITY DEFINER so callers do not need direct '
  'UPDATE permission on the is_processing column.';

-- The actual lockdown: strip the authenticated role of the right
-- to write the is_processing column directly. Other columns
-- (display_name, primary_niche, niche_ids, …) stay writable
-- under the existing ``profiles_update_own`` policy because
-- column-level REVOKE/GRANT compose with table-level GRANT —
-- we only revoke this single column.
REVOKE UPDATE (is_processing) ON public.profiles FROM authenticated;
