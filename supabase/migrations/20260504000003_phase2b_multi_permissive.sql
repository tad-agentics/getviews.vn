-- Phase 2b: Fix multiple-permissive-policy warnings.
--
-- When two PERMISSIVE policies exist for the same (role, command), Postgres
-- evaluates both for every row instead of short-circuiting. No functional
-- difference, but wasted CPU per row.
--
-- Fixes:
--   video_corpus          — "authenticated_read_corpus" was scoped to {public}
--                           (includes anon), overlapping with "anon_read_corpus".
--                           Scope it to {authenticated} only.
--   hashtag_niche_map     — "Service write" FOR ALL overlaps "Public read" on
--                           SELECT. Split into explicit write-only ops.
--   niche_candidates      — Same pattern as hashtag_niche_map.
--   draft_scripts         — "draft_scripts_modify_own" FOR ALL overlaps
--                           "draft_scripts_select_own" on SELECT. Split it.

-- ── video_corpus ──────────────────────────────────────────────────────────────
-- anon_read_corpus  → anon only (landing page, no auth required). Unchanged.
-- authenticated_read_corpus → was TO public (includes anon), now TO authenticated.

drop policy "authenticated_read_corpus" on public.video_corpus;
create policy "authenticated_read_corpus"
  on public.video_corpus for select to authenticated
  using (true);

-- ── hashtag_niche_map ─────────────────────────────────────────────────────────
-- "Public read" (SELECT, true) stays.
-- "Service write" FOR ALL was evaluated on SELECT too. Replace with explicit ops.
-- Note: service_role bypasses RLS, so these policies gate non-service writes.

drop policy "Service write" on public.hashtag_niche_map;

create policy "hashtag_niche_map_service_insert"
  on public.hashtag_niche_map for insert
  with check ((select auth.role()) = 'service_role');

create policy "hashtag_niche_map_service_update"
  on public.hashtag_niche_map for update
  using ((select auth.role()) = 'service_role');

create policy "hashtag_niche_map_service_delete"
  on public.hashtag_niche_map for delete
  using ((select auth.role()) = 'service_role');

-- ── niche_candidates ─────────────────────────────────────────────────────────
-- Same pattern as hashtag_niche_map.

drop policy "Service write" on public.niche_candidates;

create policy "niche_candidates_service_insert"
  on public.niche_candidates for insert
  with check ((select auth.role()) = 'service_role');

create policy "niche_candidates_service_update"
  on public.niche_candidates for update
  using ((select auth.role()) = 'service_role');

create policy "niche_candidates_service_delete"
  on public.niche_candidates for delete
  using ((select auth.role()) = 'service_role');

-- ── draft_scripts ─────────────────────────────────────────────────────────────
-- "draft_scripts_select_own" (SELECT) + "draft_scripts_modify_own" (ALL)
-- overlap on SELECT. Drop modify_own FOR ALL and replace with explicit
-- INSERT/UPDATE/DELETE so there is exactly one SELECT policy.

drop policy "draft_scripts_modify_own" on public.draft_scripts;

create policy "draft_scripts_insert_own"
  on public.draft_scripts for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "draft_scripts_update_own"
  on public.draft_scripts for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "draft_scripts_delete_own"
  on public.draft_scripts for delete to authenticated
  using ((select auth.uid()) = user_id);
