-- Phase C.6.1 — unified history for answer_sessions + legacy chat_sessions (server-side ordering).

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
  SELECT u.id, u.type, u.format, u.niche_id, u.title, u.turn_count, u.updated_at
  FROM (
    SELECT
      s.id,
      'answer'::text AS type,
      s.format::text,
      s.niche_id,
      s.title,
      COALESCE(tc.cnt, 0)::int AS turn_count,
      s.updated_at
    FROM public.answer_sessions s
    LEFT JOIN LATERAL (
      SELECT count(*)::int AS cnt FROM public.answer_turns t WHERE t.session_id = s.id
    ) tc ON true
    WHERE s.user_id = auth.uid() AND s.archived_at IS NULL
    UNION ALL
    SELECT
      cs.id,
      'chat'::text,
      NULL::text,
      NULL::int,
      COALESCE(cs.title, left(cs.first_message, 100)),
      COALESCE(mc.cnt, 0)::int,
      cs.updated_at
    FROM public.chat_sessions cs
    LEFT JOIN LATERAL (
      SELECT count(*)::int AS cnt FROM public.chat_messages m WHERE m.session_id = cs.id
    ) mc ON true
    WHERE cs.user_id = auth.uid()
  ) u
  WHERE (p_filter = 'all'
    OR (p_filter = 'answer' AND u.type = 'answer')
    OR (p_filter = 'chat' AND u.type = 'chat'))
    AND (p_cursor IS NULL OR u.updated_at < p_cursor)
  ORDER BY u.updated_at DESC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.history_union(TEXT, TIMESTAMPTZ, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.history_union(TEXT, TIMESTAMPTZ, INT) TO service_role;
