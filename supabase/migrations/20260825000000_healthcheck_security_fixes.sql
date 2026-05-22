-- Healthcheck security fixes (2026-05-22 repo healthcheck).
--
-- Resolves the advisor findings surfaced by get_advisors(security):
--   1 ERROR  rls_disabled_in_public          → public.batch_http_log
--   3 WARN   function_search_path_mutable     → three legacy-taxonomy mappers

-- ── 1. batch_http_log — enable RLS ───────────────────────────────────
-- Created in 20260712000000 without RLS, leaving it readable by anon +
-- authenticated via PostgREST. The table is trigger-populated by
-- _capture_batch_http_request() (SECURITY DEFINER → bypasses RLS) and read
-- only by admin_pg_net_batch_http_4xx_events() (service_role). There is no
-- legitimate anon/authenticated access. Enabling RLS with no policy denies
-- anon/authenticated while service_role and the SECURITY DEFINER trigger keep
-- working — same pattern as admin_action_log / admin_alert_* (20260502000002).
ALTER TABLE public.batch_http_log ENABLE ROW LEVEL SECURITY;

-- ── 2. Pin search_path on the legacy-taxonomy mappers ────────────────
-- These are not SECURITY DEFINER, so the risk is low, but a role-mutable
-- search_path trips the linter. Both map_* functions are pure SQL CASE
-- expressions with no schema-object references; video_corpus_fill_content_class_id
-- is a trigger that calls map_legacy_corpus_to_content_class unqualified, so it
-- needs ``public`` on the path. Pin all three to a fixed path.
ALTER FUNCTION public.map_legacy_corpus_to_content_class(integer, text)
  SET search_path = public, pg_temp;
ALTER FUNCTION public.map_legacy_niche_to_creator_niche(integer)
  SET search_path = public, pg_temp;
ALTER FUNCTION public.video_corpus_fill_content_class_id()
  SET search_path = public, pg_temp;

-- Rollback:
--   ALTER TABLE public.batch_http_log DISABLE ROW LEVEL SECURITY;
--   ALTER FUNCTION public.map_legacy_corpus_to_content_class(integer, text) RESET search_path;
--   ALTER FUNCTION public.map_legacy_niche_to_creator_niche(integer) RESET search_path;
--   ALTER FUNCTION public.video_corpus_fill_content_class_id() RESET search_path;
