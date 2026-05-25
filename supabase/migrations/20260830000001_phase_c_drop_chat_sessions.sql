-- Phase C — full chat/stream teardown (2026-05-23).
-- Drops legacy chat_sessions + chat_messages; history RPCs answer-only.

-- Retention cron no longer needed once tables are gone.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'cron-chat-archival') THEN
    PERFORM cron.unschedule('cron-chat-archival');
  END IF;
EXCEPTION
  WHEN undefined_table THEN NULL;
  WHEN undefined_function THEN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.history_union(
  p_filter TEXT DEFAULT 'all',
  p_cursor TIMESTAMPTZ DEFAULT NULL,
  p_limit INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  type TEXT,
  format TEXT,
  niche_id INT,
  title TEXT,
  turn_count INT,
  updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT
    s.id,
    'answer'::text AS type,
    s.format::text,
    s.niche_id,
    public.answer_session_list_title(s.title, s.initial_q) AS title,
    COALESCE(tc.cnt, 0)::int AS turn_count,
    s.updated_at
  FROM public.answer_sessions s
  LEFT JOIN LATERAL (
    SELECT count(*)::int AS cnt FROM public.answer_turns t WHERE t.session_id = s.id
  ) tc ON true
  WHERE s.user_id = auth.uid()
    AND s.archived_at IS NULL
    AND (p_filter IN ('all', 'answer'))
    AND (p_cursor IS NULL OR s.updated_at < p_cursor)
  ORDER BY s.updated_at DESC
  LIMIT p_limit;
$$;

CREATE OR REPLACE FUNCTION public.search_history_union(
  p_query TEXT,
  p_limit INT DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  type TEXT,
  format TEXT,
  niche_id INT,
  title TEXT,
  turn_count INT,
  updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  WITH q AS (SELECT '%' || NULLIF(btrim(p_query), '') || '%' AS pat)
  SELECT
    s.id,
    'answer'::text AS type,
    s.format::text,
    s.niche_id,
    public.answer_session_list_title(s.title, s.initial_q) AS title,
    COALESCE(tc.cnt, 0)::int AS turn_count,
    s.updated_at
  FROM public.answer_sessions s
  LEFT JOIN LATERAL (
    SELECT count(*)::int AS cnt FROM public.answer_turns t WHERE t.session_id = s.id
  ) tc ON true,
  q
  WHERE s.user_id = auth.uid()
    AND s.archived_at IS NULL
    AND q.pat IS NOT NULL
    AND (s.title ILIKE q.pat OR s.initial_q ILIKE q.pat)
  ORDER BY s.updated_at DESC
  LIMIT GREATEST(1, LEAST(p_limit, 100));
$$;

COMMENT ON FUNCTION public.search_history_union(TEXT, INT) IS
  'Phase C — answer_sessions search only (title + initial_q). Same row shape as history_union.';

GRANT EXECUTE ON FUNCTION public.history_union(TEXT, TIMESTAMPTZ, INT) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.search_history_union(TEXT, INT) TO authenticated, service_role;

DROP INDEX IF EXISTS public.idx_chat_messages_content_trgm;

DROP TABLE IF EXISTS public.chat_messages CASCADE;
DROP TABLE IF EXISTS public.chat_sessions CASCADE;
DROP TABLE IF EXISTS public.chat_archival_audit CASCADE;

-- Orphan RPCs / trigger helpers (search_sessions is a FUNCTION, not a table).
DROP FUNCTION IF EXISTS public.search_sessions(text, uuid);
DROP FUNCTION IF EXISTS public.set_chat_sessions_updated_at() CASCADE;
DROP FUNCTION IF EXISTS public.soft_delete_chat_session(uuid);
