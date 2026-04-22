-- Phase 5: Pin search_path on all SECURITY DEFINER functions.
--
-- A SECURITY DEFINER function runs with the privileges of its owner (postgres).
-- If search_path is mutable, an attacker who can create objects in a schema
-- earlier in the path can shadow built-ins or trusted functions. Pinning to
-- (public, pg_temp) prevents this.
--
-- Exact signatures from pg_proc — verified via Management API before writing.

alter function public.decrement_and_grant_credits(
  p_payos_order_code text,
  p_payos_payment_id text,
  p_event_type       text
) set search_path = public, pg_temp;

alter function public.decrement_credit(
  p_user_id uuid
) set search_path = public, pg_temp;

alter function public.get_weekly_trend_summaries(
  p_week_of date
) set search_path = public, pg_temp;

alter function public.handle_new_user()
  set search_path = public, pg_temp;

alter function public.increment_free_query_count(
  p_user_id uuid
) set search_path = public, pg_temp;

alter function public.invalidate_creator_velocity_match_score()
  set search_path = public, pg_temp;

alter function public.refresh_niche_intelligence()
  set search_path = public, pg_temp;

alter function public.search_sessions(
  search_query text,
  p_user_id    uuid
) set search_path = public, pg_temp;

alter function public.seed_starter_creators(
  p_top_n integer
) set search_path = public, pg_temp;

alter function public.set_session_first_message_from_user_message()
  set search_path = public, pg_temp;

alter function public.toggle_reference_channel(
  p_handle text
) set search_path = public, pg_temp;
