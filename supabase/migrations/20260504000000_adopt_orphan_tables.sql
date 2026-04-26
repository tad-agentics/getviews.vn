-- Phase 0: Codify 5 tables that exist in prod but were created via the Supabase
-- dashboard SQL editor without a migration file. All are currently empty.
-- Using CREATE TABLE IF NOT EXISTS makes this a no-op against prod and correctly
-- recreates them on a fresh dev DB so the repo is the single source of truth.

create table if not exists public.competitor_tracking (
  id                uuid        primary key default gen_random_uuid(),
  user_id           uuid        not null references public.profiles(id) on delete cascade,
  competitor_handle text        not null,
  niche_id          integer     references public.niche_taxonomy(id),
  added_at          timestamptz not null default now(),
  last_checked_at   timestamptz,
  last_hook_type    text,
  last_format       text
);

create table if not exists public.creator_pattern (
  id                      uuid        primary key default gen_random_uuid(),
  user_id                 uuid        not null references public.profiles(id) on delete cascade,
  tiktok_handle           text        not null,
  niche_id                integer     references public.niche_taxonomy(id),
  computed_at             timestamptz not null default now(),
  recent_video_count      integer,
  dominant_hook_type      text,
  hook_type_distribution  jsonb,
  dominant_format         text,
  format_distribution     jsonb,
  avg_posting_hour        real,
  avg_views               bigint,
  views_trend             text,
  views_trend_data        jsonb,
  avg_save_rate           real,
  save_rate_vs_niche      real,
  untried_formats         jsonb,
  repeating_pattern       text
);

create table if not exists public.niche_daily_sounds (
  id               uuid    primary key default gen_random_uuid(),
  niche_id         integer not null references public.niche_taxonomy(id),
  computed_date    date    not null,
  top_sounds_3d    jsonb,
  top_sounds_7d    jsonb,
  emerging_sounds  jsonb,
  computed_at      timestamptz not null default now(),
  sound_insight_text text,
  unique (niche_id, computed_date)
);

create table if not exists public.niche_weekly_digest (
  id                         uuid    primary key default gen_random_uuid(),
  niche_id                   integer not null references public.niche_taxonomy(id),
  week_of                    date    not null,
  top_formula_json           jsonb,
  formula_changed            boolean default false,
  previous_top_formula_json  jsonb,
  top_sounds_json            jsonb,
  new_sounds_json            jsonb,
  carousel_count             integer,
  video_count                integer,
  carousel_avg_views         bigint,
  video_avg_views            bigint,
  carousel_avg_save_rate     real,
  video_avg_save_rate        real,
  best_posting_hours_json    jsonb,
  total_videos_indexed       integer,
  avg_views                  bigint,
  avg_save_rate              real,
  computed_at                timestamptz not null default now(),
  niche_insight_text         text,
  formula_structural_pattern jsonb,
  cross_niche_signals        jsonb,
  unique (niche_id, week_of)
);

create table if not exists public.push_events (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references public.profiles(id) on delete cascade,
  event_type  text        not null,
  event_data  jsonb,
  created_at  timestamptz not null default now(),
  read_at     timestamptz,
  sent_email  boolean     default false,
  sent_inapp  boolean     default false
);
