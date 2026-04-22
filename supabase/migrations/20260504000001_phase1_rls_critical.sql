-- Phase 1: Critical security fixes
--
-- 1.1  Enable RLS + sensible policies on the 5 orphan tables.
-- 1.2  Revoke niche_intelligence MV access from anon/authenticated
--      (only ever queried via service client in report_pattern_compute.py).
-- 1.3  Pin search_path on 3 trigger/aggregate functions flagged by advisor.

-- ── 1.1 competitor_tracking ───────────────────────────────────────────────────
-- User-owned watchlist; writes are service-only (service_role bypasses RLS).

alter table public.competitor_tracking enable row level security;

create policy "competitor_tracking_select_own"
  on public.competitor_tracking for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "competitor_tracking_insert_own"
  on public.competitor_tracking for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "competitor_tracking_update_own"
  on public.competitor_tracking for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "competitor_tracking_delete_own"
  on public.competitor_tracking for delete to authenticated
  using ((select auth.uid()) = user_id);

create index if not exists idx_competitor_tracking_user_id
  on public.competitor_tracking (user_id);

create index if not exists idx_competitor_tracking_niche_id
  on public.competitor_tracking (niche_id);

-- ── 1.1 creator_pattern ───────────────────────────────────────────────────────
-- User-owned computed snapshots; batch writes use service_role (bypasses RLS).

alter table public.creator_pattern enable row level security;

create policy "creator_pattern_select_own"
  on public.creator_pattern for select to authenticated
  using ((select auth.uid()) = user_id);

create index if not exists idx_creator_pattern_user_id
  on public.creator_pattern (user_id);

create index if not exists idx_creator_pattern_niche_id
  on public.creator_pattern (niche_id);

-- ── 1.1 niche_daily_sounds ────────────────────────────────────────────────────
-- Niche-level batch output; authenticated read, service_role writes.

alter table public.niche_daily_sounds enable row level security;

create policy "niche_daily_sounds_read"
  on public.niche_daily_sounds for select to authenticated
  using (true);

create index if not exists idx_niche_daily_sounds_niche_date
  on public.niche_daily_sounds (niche_id, computed_date desc);

-- ── 1.1 niche_weekly_digest ───────────────────────────────────────────────────
-- Niche-level batch output; authenticated read, service_role writes.

alter table public.niche_weekly_digest enable row level security;

create policy "niche_weekly_digest_read"
  on public.niche_weekly_digest for select to authenticated
  using (true);

create index if not exists idx_niche_weekly_digest_niche_week
  on public.niche_weekly_digest (niche_id, week_of desc);

-- ── 1.1 push_events ──────────────────────────────────────────────────────────
-- User-owned notifications; service_role writes (via batch), user marks as read.

alter table public.push_events enable row level security;

create policy "push_events_select_own"
  on public.push_events for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "push_events_update_own_read_state"
  on public.push_events for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create index if not exists idx_push_events_user_unread
  on public.push_events (user_id, created_at desc)
  where read_at is null;

-- ── 1.2 niche_intelligence MV ────────────────────────────────────────────────
-- Materialized view queried exclusively by report_pattern_compute.py via
-- service client. No frontend reads. Revoke from client-facing roles.

revoke select on public.niche_intelligence from anon, authenticated;

-- ── 1.3 Pin search_path on trigger/aggregate functions ────────────────────────

alter function public.set_chat_sessions_updated_at()
  set search_path = public, pg_temp;

alter function public.set_profiles_updated_at()
  set search_path = public, pg_temp;

alter function public.cross_creator_pattern_aggregate(integer)
  set search_path = public, pg_temp;
