-- Fix: 5 duplicate indexes introduced in Phase 1 because the orphan tables
-- already had indexes created via the dashboard SQL editor. Drop our redundant
-- copies and keep the pre-existing ones.
--
-- Fix: profiles FK index not created in Phase 3 because the column is named
-- `primary_niche`, not `primary_niche_id` (changed by migration 20260410000012).

-- ── Drop our redundant Phase-1 indexes ───────────────────────────────────────
-- Each pair below is identical; we drop the one we added, keep the pre-existing.

drop index if exists public.idx_competitor_tracking_user_id; -- dups idx_competitor_user
drop index if exists public.idx_creator_pattern_user_id;     -- dups idx_creator_pattern_user
drop index if exists public.idx_niche_daily_sounds_niche_date; -- dups idx_daily_sounds_lookup
drop index if exists public.idx_niche_weekly_digest_niche_week; -- dups idx_niche_digest_lookup
drop index if exists public.idx_push_events_user_unread;     -- dups idx_push_unread

-- ── Add missing profiles FK index ─────────────────────────────────────────────
-- FK constraint: fk_profiles_primary_niche → niche_taxonomy(id) ON DELETE SET NULL
-- Column is `primary_niche` (integer), set in migration 20260410000012.

create index if not exists idx_profiles_primary_niche
  on public.profiles (primary_niche);
