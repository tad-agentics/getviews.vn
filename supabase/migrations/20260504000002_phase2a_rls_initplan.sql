-- Phase 2a: Fix RLS init-plan anti-pattern across all flagged tables.
--
-- Every policy that calls auth.uid() or auth.role() directly re-evaluates the
-- function for every row in the result set. Wrapping in (select auth.uid())
-- causes the planner to treat it as an init-plan: evaluated once per query.
-- Invisible at current row counts (<2k rows), material at 100k+.
--
-- Pattern: drop the policy, recreate with (select auth.uid()).
-- All policies keep their original name so no application changes are needed.

-- ── answer_sessions ───────────────────────────────────────────────────────────

drop policy "answer_sessions_select_own" on public.answer_sessions;
create policy "answer_sessions_select_own"
  on public.answer_sessions for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy "answer_sessions_insert_own" on public.answer_sessions;
create policy "answer_sessions_insert_own"
  on public.answer_sessions for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy "answer_sessions_update_own" on public.answer_sessions;
create policy "answer_sessions_update_own"
  on public.answer_sessions for update to authenticated
  using ((select auth.uid()) = user_id);

-- ── answer_turns ──────────────────────────────────────────────────────────────

drop policy "answer_turns_select_own" on public.answer_turns;
create policy "answer_turns_select_own"
  on public.answer_turns for select to authenticated
  using (
    (select auth.uid()) = (
      select answer_sessions.user_id
      from public.answer_sessions
      where answer_sessions.id = answer_turns.session_id
    )
  );

-- ── channel_formulas ─────────────────────────────────────────────────────────

drop policy "Authenticated users read channel_formulas" on public.channel_formulas;
create policy "Authenticated users read channel_formulas"
  on public.channel_formulas for select to authenticated
  using ((select auth.uid()) is not null);

-- ── chat_messages ─────────────────────────────────────────────────────────────

drop policy "Users read own messages" on public.chat_messages;
create policy "Users read own messages"
  on public.chat_messages for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy "chat_messages_insert_own_session" on public.chat_messages;
create policy "chat_messages_insert_own_session"
  on public.chat_messages for insert to authenticated
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.chat_sessions
      where chat_sessions.id = chat_messages.session_id
        and chat_sessions.user_id = (select auth.uid())
    )
  );

-- ── chat_sessions ─────────────────────────────────────────────────────────────

drop policy "Users read own sessions" on public.chat_sessions;
create policy "Users read own sessions"
  on public.chat_sessions for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy "Users insert own sessions" on public.chat_sessions;
create policy "Users insert own sessions"
  on public.chat_sessions for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy "Users update own sessions" on public.chat_sessions;
create policy "Users update own sessions"
  on public.chat_sessions for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy "Users delete own sessions" on public.chat_sessions;
create policy "Users delete own sessions"
  on public.chat_sessions for delete to authenticated
  using ((select auth.uid()) = user_id);

-- ── creator_velocity ──────────────────────────────────────────────────────────

drop policy "Authenticated users read creator_velocity" on public.creator_velocity;
create policy "Authenticated users read creator_velocity"
  on public.creator_velocity for select to authenticated
  using ((select auth.uid()) is not null);

-- ── credit_transactions ───────────────────────────────────────────────────────

drop policy "Users read own credit transactions" on public.credit_transactions;
create policy "Users read own credit transactions"
  on public.credit_transactions for select to authenticated
  using ((select auth.uid()) = user_id);

-- ── cross_creator_patterns ────────────────────────────────────────────────────

drop policy "cross_creator_patterns_select" on public.cross_creator_patterns;
create policy "cross_creator_patterns_select"
  on public.cross_creator_patterns for select to authenticated
  using ((select auth.uid()) is not null);

-- ── daily_ritual ──────────────────────────────────────────────────────────────

drop policy "Users read own daily_ritual" on public.daily_ritual;
create policy "Users read own daily_ritual"
  on public.daily_ritual for select to authenticated
  using ((select auth.uid()) = user_id);

-- ── draft_scripts (select_own only; modify_own handled in Phase 2b) ───────────

drop policy "draft_scripts_select_own" on public.draft_scripts;
create policy "draft_scripts_select_own"
  on public.draft_scripts for select to authenticated
  using ((select auth.uid()) = user_id);

-- ── format_lifecycle ──────────────────────────────────────────────────────────

drop policy "Authenticated users read format_lifecycle" on public.format_lifecycle;
create policy "Authenticated users read format_lifecycle"
  on public.format_lifecycle for select to authenticated
  using ((select auth.uid()) is not null);

-- ── hook_effectiveness ────────────────────────────────────────────────────────

drop policy "Authenticated users read hook_effectiveness" on public.hook_effectiveness;
create policy "Authenticated users read hook_effectiveness"
  on public.hook_effectiveness for select to authenticated
  using ((select auth.uid()) is not null);

-- ── profiles ──────────────────────────────────────────────────────────────────

drop policy "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id);

drop policy "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
  on public.profiles for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- ── scene_intelligence ────────────────────────────────────────────────────────

drop policy "Authenticated users read scene_intelligence" on public.scene_intelligence;
create policy "Authenticated users read scene_intelligence"
  on public.scene_intelligence for select to authenticated
  using ((select auth.uid()) is not null);

-- ── signal_grades ─────────────────────────────────────────────────────────────

drop policy "Authenticated users read signal_grades" on public.signal_grades;
create policy "Authenticated users read signal_grades"
  on public.signal_grades for select to authenticated
  using ((select auth.uid()) is not null);

-- ── starter_creators ──────────────────────────────────────────────────────────

drop policy "Authenticated users read starter_creators" on public.starter_creators;
create policy "Authenticated users read starter_creators"
  on public.starter_creators for select to authenticated
  using ((select auth.uid()) is not null);

-- ── subscriptions ─────────────────────────────────────────────────────────────

drop policy "Users read own subscriptions" on public.subscriptions;
create policy "Users read own subscriptions"
  on public.subscriptions for select to authenticated
  using ((select auth.uid()) = user_id);

-- ── trend_velocity ────────────────────────────────────────────────────────────

drop policy "Authenticated users read trend_velocity" on public.trend_velocity;
create policy "Authenticated users read trend_velocity"
  on public.trend_velocity for select to authenticated
  using ((select auth.uid()) is not null);

-- ── usage_events ──────────────────────────────────────────────────────────────

drop policy "usage_events_insert_own" on public.usage_events;
create policy "usage_events_insert_own"
  on public.usage_events for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy "usage_events_select_own" on public.usage_events;
create policy "usage_events_select_own"
  on public.usage_events for select to authenticated
  using ((select auth.uid()) = user_id);

-- ── video_diagnostics ─────────────────────────────────────────────────────────

drop policy "Authenticated users can read video_diagnostics" on public.video_diagnostics;
create policy "Authenticated users can read video_diagnostics"
  on public.video_diagnostics for select to authenticated
  using ((select auth.uid()) is not null);

-- ── video_dang_hoc ────────────────────────────────────────────────────────────

drop policy "video_dang_hoc_select" on public.video_dang_hoc;
create policy "video_dang_hoc_select"
  on public.video_dang_hoc for select to authenticated
  using ((select auth.uid()) is not null);

-- ── video_patterns ────────────────────────────────────────────────────────────

drop policy "Authenticated users read video_patterns" on public.video_patterns;
create policy "Authenticated users read video_patterns"
  on public.video_patterns for select to authenticated
  using ((select auth.uid()) is not null);
