-- Advisor follow-ups (2026-05-22): tighten EXECUTE / SELECT grants flagged by
-- get_advisors(security) — anon/authenticated_security_definer_function_executable
-- and materialized_view_in_api.
--
-- Approach: revoke EXECUTE from anon (and from authenticated where the function
-- is never called by a logged-in user — triggers, cron, batch, and Edge/Cloud
-- Run service_role paths). service_role keeps its own explicit grant in every
-- case (verified via pg_proc.proacl), so Cloud Run + Edge Functions are
-- unaffected. PUBLIC is included in the revoke so no grant survives by
-- inheritance. Caller roles were verified by tracing each function:
--   user_supabase().rpc(...) = authenticated; Edge Function / Cloud Run service
--   client = service_role; trigger functions fire via the trigger mechanism and
--   need no EXECUTE grant at all.

-- ── Group 1 — never user-callable: revoke anon + authenticated + PUBLIC ──────
-- Triggers (fire as table owner; no role needs EXECUTE):
REVOKE EXECUTE ON FUNCTION public._capture_batch_http_request() FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.set_session_first_message_from_user_message() FROM anon, authenticated, PUBLIC;
-- Internal / cron helpers:
REVOKE EXECUTE ON FUNCTION public._prune_batch_http_log() FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(integer) FROM anon, authenticated, PUBLIC;
-- Batch (Cloud Run service_role):
REVOKE EXECUTE ON FUNCTION public.upsert_video_corpus_batch(jsonb) FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.seed_starter_creators(integer) FROM anon, authenticated, PUBLIC;
-- Edge Functions (service_role): cron-monday-email, payos-webhook:
REVOKE EXECUTE ON FUNCTION public.get_weekly_trend_summaries(date) FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.decrement_and_grant_credits(text, text, text) FROM anon, authenticated, PUBLIC;
-- Admin RPC read by Cloud Run service_role only:
REVOKE EXECUTE ON FUNCTION public.admin_pg_net_batch_http_4xx_events(integer) FROM anon, authenticated, PUBLIC;

-- ── Group 2 — genuine logged-in RPCs: revoke anon + PUBLIC, KEEP authenticated ─
-- Credit / processing lock RPCs, called via user_supabase() (authenticated):
REVOKE EXECUTE ON FUNCTION public.begin_processing(uuid) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.end_processing(uuid) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.decrement_credit(uuid) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.increment_free_query_count(uuid) FROM anon, PUBLIC;
-- Admin panel RPCs, called from the FE supabase client (authenticated admin):
REVOKE EXECUTE ON FUNCTION public.thumbnail_failures_count_7d(timestamp with time zone) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.thumbnail_failures_top10(timestamp with time zone) FROM anon, PUBLIC;
-- No caller found in FE/Edge/Cloud Run, but keep authenticated to avoid breaking
-- an admin/legacy path that grep missed; anon is never legitimate:
REVOKE EXECUTE ON FUNCTION public.admin_flush_video_diagnostics_cache(text) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.search_sessions(text, uuid) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.toggle_reference_channel(text) FROM anon, PUBLIC;

-- ── Materialized views exposed via PostgREST (materialized_view_in_api) ───────
-- Only Cloud Run (service_role) reads these two — revoke both API roles:
REVOKE SELECT ON public.content_class_tier_intelligence FROM anon, authenticated;
REVOKE SELECT ON public.creator_niche_content_class_stats FROM anon, authenticated;
-- content_class_intelligence is read client-side by useTopNiches /
-- useContentClassIntelligence / useClassMorningSignals (authenticated). Keep
-- authenticated; drop anon (those hooks never run on landing/auth routes).
REVOKE SELECT ON public.content_class_intelligence FROM anon;

-- Not addressed here (require non-SQL action — see PR notes):
--   * extension_in_public (pg_net): moving schemas risks breaking pg_cron
--     net.http_post and the batch HTTP-capture trigger; left in place by design.
--   * auth_leaked_password_protection: Supabase Auth dashboard / Management API
--     toggle, not a DB migration.
--   * rls_enabled_no_policy (15 INFO): intentional deny-all on service-role-only
--     tables; adding policies would loosen, not harden. No action.
