-- Phase D.6.1 — profiles.is_admin + self-promotion guard.
--
-- Adds an admin flag to profiles without opening a path for users to flip
-- it on themselves. The column-level REVOKE keeps `authenticated` role
-- out of UPDATE (is_admin) entirely; service_role (and dashboard SQL
-- editor) remains the only writer. Combined with the existing
-- profiles_update_own RLS policy this means:
--
--   - End user's profile SELECT still returns is_admin (so the SPA can
--     gate the /app/admin route locally).
--   - End user's profile UPDATE silently no-ops on is_admin (the column
--     grant is missing), so a malicious client that POSTs
--     { is_admin: true } with their own JWT gets a "permission denied
--     for column" error, not a successful elevation.
--
-- Promoting an admin:
--
--   SET ROLE service_role;  -- or run from the Supabase SQL editor as
--                           -- service_role, which is the default there.
--   UPDATE public.profiles SET is_admin = true WHERE id = '<user-uuid>';
--   RESET ROLE;
--
-- Demoting is the same with is_admin = false.

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- Column-level revoke keeps the authenticated role off UPDATE (is_admin)
-- even though the row-level UPDATE policy would otherwise allow it. This
-- is the narrow fix — we don't need to rewrite profiles_update_own.
REVOKE UPDATE (is_admin) ON public.profiles FROM authenticated;

-- Partial index: every admin check is "where is_admin = true" — filtering
-- it saves an index scan on the 99.99% of rows where it's false.
CREATE INDEX IF NOT EXISTS profiles_is_admin_idx
  ON public.profiles (id)
  WHERE is_admin = true;

COMMENT ON COLUMN public.profiles.is_admin IS
  'Phase D.6.1 admin flag. Read-exposed to authenticated (the SPA uses it '
  'to gate /app/admin locally); UPDATE (is_admin) is REVOKE-d from '
  'authenticated so a malicious client cannot self-promote. Flip via '
  'service_role only (Supabase SQL editor, or service-role keyed client).';
