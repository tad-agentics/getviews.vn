-- Phase D.2.4 — cross-type history search + GIN indexes for ILIKE performance.
--
-- `search_sessions` (C.6 MVP) only searched `chat_sessions.title` +
-- `chat_sessions.first_message`. The `/history` screen now covers both
-- answer_sessions (D-era research) and legacy chat_sessions, so a single
-- search box must OR across both types plus `chat_messages.content`.
--
-- Shape matches `history_union` so the frontend can swap the data source
-- without reshaping rows. Ordering is `updated_at DESC`; page size matches
-- the paginated list (50).
--
-- Performance: trigram GIN indexes on the three ILIKE columns so leading
-- wildcards don't force a seq scan as the corpus of sessions grows.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_answer_sessions_title_trgm
  ON public.answer_sessions USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_answer_sessions_initial_q_trgm
  ON public.answer_sessions USING GIN (initial_q gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_chat_messages_content_trgm
  ON public.chat_messages USING GIN (content gin_trgm_ops);


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
  WITH
    q AS (SELECT '%' || NULLIF(btrim(p_query), '') || '%' AS pat),
    matched_answer AS (
      SELECT s.id
      FROM public.answer_sessions s, q
      WHERE s.user_id = auth.uid()
        AND s.archived_at IS NULL
        AND q.pat IS NOT NULL
        AND (s.title ILIKE q.pat OR s.initial_q ILIKE q.pat)
    ),
    matched_chat AS (
      SELECT DISTINCT cs.id
      FROM public.chat_sessions cs
      LEFT JOIN public.chat_messages m ON m.session_id = cs.id,
      q
      WHERE cs.user_id = auth.uid()
        AND COALESCE(cs.deleted_at, NULL) IS NULL
        AND q.pat IS NOT NULL
        AND (
          cs.title ILIKE q.pat
          OR cs.first_message ILIKE q.pat
          OR m.content ILIKE q.pat
        )
    )
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
    JOIN matched_answer ma ON ma.id = s.id
    LEFT JOIN LATERAL (
      SELECT count(*)::int AS cnt FROM public.answer_turns t WHERE t.session_id = s.id
    ) tc ON TRUE
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
    JOIN matched_chat mc_ids ON mc_ids.id = cs.id
    LEFT JOIN LATERAL (
      SELECT count(*)::int AS cnt FROM public.chat_messages m WHERE m.session_id = cs.id
    ) mc ON TRUE
  ) u
  ORDER BY u.updated_at DESC
  LIMIT GREATEST(1, LEAST(p_limit, 100));
$$;

GRANT EXECUTE ON FUNCTION public.search_history_union(TEXT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_history_union(TEXT, INT) TO service_role;

COMMENT ON FUNCTION public.search_history_union(TEXT, INT) IS
  'D.2.4 — cross-type history search. ORs over answer_sessions.title / '
  'answer_sessions.initial_q / chat_sessions.title / chat_sessions.first_message / '
  'chat_messages.content, RLS-bounded via auth.uid(). Returns the same shape as '
  'history_union(); paging defers to a fresh call for now (query-typing UX).';
