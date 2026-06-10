-- Widen the pg_net batch watch from 4xx-only to ALL HTTP errors (>=400).
--
-- Audit 2026-06-10 P-1: cron-batch-process-ingest-queue returned **500**
-- nightly for ~7 weeks (missing table) and the 4xx-only watch never fired.
-- 5xx from a /batch/* call is exactly as silent and exactly as fatal as a
-- 4xx — widen both the assert helper and the admin-alert RPC.

CREATE OR REPLACE FUNCTION public.admin_pg_net_batch_http_4xx_events(p_hours int DEFAULT 6)
RETURNS TABLE (
  response_id bigint,
  status_code int,
  created_at timestamptz,
  request_url text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = net, public
AS $$
  SELECT
    r.id,
    r.status_code,
    r.created,
    q.url
  FROM net._http_response r
  INNER JOIN net.http_request_queue q ON q.id = r.id
  WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
    AND r.status_code >= 400
    AND q.url ILIKE '%/batch/%';
$$;

COMMENT ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) IS
  'Returns recent pg_net HTTP >=400 rows whose request URL targets /batch/* (admin alert + debugging). Name kept for rule-key compatibility; covers 5xx since 2026-06-10.';

CREATE OR REPLACE FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(p_hours int DEFAULT 3)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = net, public
AS $$
DECLARE
  n int;
  sample text;
BEGIN
  SELECT count(*)::int INTO n
  FROM net._http_response r
  INNER JOIN net.http_request_queue q ON q.id = r.id
  WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
    AND r.status_code >= 400
    AND q.url ILIKE '%/batch/%';

  IF n > 0 THEN
    SELECT string_agg(
      format('%s @ %s', r.status_code::text, left(r.created::text, 19)),
      ' | '
      ORDER BY r.created DESC
    ) INTO sample
    FROM (
      SELECT r.status_code, r.created
      FROM net._http_response r
      INNER JOIN net.http_request_queue q ON q.id = r.id
      WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
        AND r.status_code >= 400
        AND q.url ILIKE '%/batch/%'
      ORDER BY r.created DESC
      LIMIT 5
    ) r;

    RAISE EXCEPTION
      USING message = format(
        'pg_net: %s batch HTTP errors (>=400) in last %s h (status@time sample): %s',
        n, p_hours, sample
      );
  END IF;
END;
$$;

COMMENT ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) IS
  'pg_cron helper: raises if recent /batch/* pg_net calls returned HTTP >=400 (4xx AND 5xx since 2026-06-10).';
