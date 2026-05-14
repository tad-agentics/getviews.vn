-- Document the deny-all access posture on ``thumbnail_failures``.
--
-- The migration that created the table enabled RLS but defined zero
-- policies — Supabase's deny-by-default behaviour does the right thing
-- (no client JWT can read or write), but the lack of explicit policies
-- means a future contributor who tries to add a direct insert from the
-- FE gets a cryptic ``permission denied for table`` error with no
-- breadcrumb explaining why. Add explicit deny-all policies as
-- self-documentation.
--
-- The Edge Function uses ``service_role`` and bypasses RLS at the
-- session level. The admin SECURITY DEFINER RPCs also bypass RLS at
-- the function level. Both paths are unaffected.

CREATE POLICY "deny_all_anon_thumbnail_failures"
  ON public.thumbnail_failures
  FOR ALL
  TO anon
  USING (false)
  WITH CHECK (false);

CREATE POLICY "deny_all_authenticated_thumbnail_failures"
  ON public.thumbnail_failures
  FOR ALL
  TO authenticated
  USING (false)
  WITH CHECK (false);

COMMENT ON POLICY "deny_all_anon_thumbnail_failures" ON public.thumbnail_failures IS
  'Self-documenting deny-all policy. Direct client access is blocked; '
  'reads go through SECURITY DEFINER RPCs, writes through the '
  'track-thumbnail-failure Edge Function with service_role.';

COMMENT ON POLICY "deny_all_authenticated_thumbnail_failures" ON public.thumbnail_failures IS
  'Self-documenting deny-all policy. Direct client access is blocked; '
  'reads go through SECURITY DEFINER RPCs, writes through the '
  'track-thumbnail-failure Edge Function with service_role.';
