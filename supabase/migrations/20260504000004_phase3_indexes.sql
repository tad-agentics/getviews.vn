-- Phase 3: Index hygiene.
--
-- 3.1 Drop 4 duplicate indexes (identical predicate, different name).
--     Duplicates waste space and slow down every INSERT/UPDATE/DELETE on the table.
--
-- 3.2 Add 15 covering indexes for unindexed foreign keys.
--     ON DELETE CASCADE and FK-join queries issue seq scans without them.
--
-- Note: We intentionally keep all GIN/trgm/search-vector indexes even though
--       pg_stat_user_indexes shows 0 scans — they back the history search
--       feature (search_sessions RPC) which has not yet been heavily exercised.

-- ── 3.1 Drop duplicate indexes ────────────────────────────────────────────────

-- subscriptions: idx_subscriptions_payos_order duplicates the UNIQUE constraint
-- subscriptions_payos_order_code_key (same column: payos_order_code).
drop index if exists public.idx_subscriptions_payos_order;

-- video_corpus: idx_corpus_caption_text duplicates idx_corpus_caption.
drop index if exists public.idx_corpus_caption_text;

-- video_corpus: idx_corpus_vi_hashtags duplicates idx_corpus_specific_hashtags.
drop index if exists public.idx_corpus_vi_hashtags;

-- video_corpus: idx_corpus_video_id duplicates the UNIQUE constraint
-- video_corpus_video_id_key (same column: video_id).
drop index if exists public.idx_corpus_video_id;

-- ── 3.2 Covering indexes for unindexed foreign keys ──────────────────────────

-- answer_session_idempotency.session_id — ON DELETE CASCADE from answer_sessions.
create index if not exists idx_answer_session_idempotency_session_id
  on public.answer_session_idempotency (session_id);

-- answer_sessions.niche_id — FK + filter in analytics queries.
create index if not exists idx_answer_sessions_niche_id
  on public.answer_sessions (niche_id);

-- competitor_tracking: FK indexes added in Phase 1.

-- creator_velocity.niche_id — FK + filter in batch analytics.
create index if not exists idx_creator_velocity_niche_id
  on public.creator_velocity (niche_id);

-- credit_transactions.session_id — ON DELETE SET NULL from chat_sessions.
create index if not exists idx_credit_transactions_session_id
  on public.credit_transactions (session_id);

-- credit_transactions.subscription_id — FK from subscriptions.
create index if not exists idx_credit_transactions_subscription_id
  on public.credit_transactions (subscription_id);

-- daily_ritual.niche_id — FK + filter.
create index if not exists idx_daily_ritual_niche_id
  on public.daily_ritual (niche_id);

-- draft_scripts.niche_id — FK + filter in user's script list.
create index if not exists idx_draft_scripts_niche_id
  on public.draft_scripts (niche_id);

-- draft_scripts.source_session_id — ON DELETE SET NULL from answer_sessions.
create index if not exists idx_draft_scripts_source_session_id
  on public.draft_scripts (source_session_id);

-- format_lifecycle.niche_id — FK + filter.
create index if not exists idx_format_lifecycle_niche_id
  on public.format_lifecycle (niche_id);

-- gemini_calls.user_id — used by admin analytics in routers/admin.py.
create index if not exists idx_gemini_calls_user_id
  on public.gemini_calls (user_id);

-- hashtag_niche_map.niche_id — FK + join in hashtag_niche_map.py queries.
create index if not exists idx_hashtag_niche_map_niche_id
  on public.hashtag_niche_map (niche_id);

-- niche_candidates.assigned_niche_id — FK from niche_taxonomy.
create index if not exists idx_niche_candidates_assigned_niche_id
  on public.niche_candidates (assigned_niche_id);

-- profiles.primary_niche_id — FK from niche_taxonomy; used in niche_match.py.
-- Column may be named primary_niche_id or fk_profiles_primary_niche target;
-- use IF NOT EXISTS so this is a no-op if the column name differs.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name   = 'profiles'
      and column_name  = 'primary_niche_id'
  ) then
    execute 'create index if not exists idx_profiles_primary_niche_id
             on public.profiles (primary_niche_id)';
  end if;
end
$$;
