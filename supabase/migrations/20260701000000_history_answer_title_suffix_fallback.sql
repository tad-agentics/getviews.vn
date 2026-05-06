-- ISSUE-014 — History / history_union showed nonsense titles like "ơn" when
-- ``answer_sessions.title`` matched only a trailing fragment of
-- ``initial_q`` (e.g. last graphemes of "Cảm ơn …"). List + search RPCs
-- now derive a display title that prefers ``initial_q`` in that case.
-- Optional one-off repair updates stored ``title`` for the same pattern.

CREATE OR REPLACE FUNCTION public.answer_session_list_title(p_title text, p_initial_q text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = public
AS $$
  SELECT LEFT(
    CASE
      WHEN TRIM(COALESCE(p_initial_q, '')) = '' THEN TRIM(COALESCE(p_title, ''))
      WHEN TRIM(COALESCE(p_title, '')) = '' THEN TRIM(p_initial_q)
      WHEN LENGTH(TRIM(p_title)) <= 8
           AND LENGTH(TRIM(p_initial_q)) > LENGTH(TRIM(p_title)) + 5
           AND LEFT(TRIM(p_initial_q), LENGTH(TRIM(p_title))) <> TRIM(p_title)
           AND RIGHT(TRIM(p_initial_q), LENGTH(TRIM(p_title))) = TRIM(p_title)
        THEN TRIM(p_initial_q)
      ELSE COALESCE(NULLIF(TRIM(p_title), ''), TRIM(p_initial_q))
    END,
    120
  );
$$;

COMMENT ON FUNCTION public.answer_session_list_title(text, text) IS
  'History list label: prefer initial_q when stored title is a short trailing substring of initial_q (ISSUE-014).';

GRANT EXECUTE ON FUNCTION public.answer_session_list_title(text, text) TO authenticated, service_role;

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
      public.answer_session_list_title(s.title, s.initial_q) AS title,
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
      public.answer_session_list_title(s.title, s.initial_q) AS title,
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

-- Repair persisted rows so detail / sidebar (raw ``title``) are sane too.
UPDATE public.answer_sessions s
SET title = CASE
  WHEN length(trim(s.initial_q)) > 80 THEN left(trim(s.initial_q), 80) || '…'
  ELSE trim(s.initial_q)
END
WHERE trim(coalesce(s.title, '')) <> ''
  AND trim(coalesce(s.initial_q, '')) <> ''
  AND length(trim(s.title)) <= 8
  AND length(trim(s.initial_q)) > length(trim(s.title)) + 5
  AND left(trim(s.initial_q), length(trim(s.title))) <> trim(s.title)
  AND right(trim(s.initial_q), length(trim(s.title))) = trim(s.title);
