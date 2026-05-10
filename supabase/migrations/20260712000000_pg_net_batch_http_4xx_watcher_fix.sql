-- Fix: pg_net batch 4xx watcher detects failures past the request-queue GC window.
--
-- Root cause of the silent-401 incident (2026-05-02 to 2026-05-09):
--   cron_assert_no_recent_pg_net_batch_http_4xx (and its backing RPC
--   admin_pg_net_batch_http_4xx_events) joined net._http_response to
--   net.http_request_queue. pg_net GCs the request queue immediately
--   after response storage — so by the time the hourly watcher runs,
--   the join always returns 0 rows and RAISES nothing even when every
--   batch request is returning 401.
--
-- Fix: capture /batch/* request URLs into public.batch_http_log via a
-- trigger that fires AFTER INSERT ON net.http_request_queue (before GC).
-- The log persists for 7 days. Both the assert function and the admin
-- RPC are updated to join against batch_http_log instead.
--
-- Also adds URL to the RAISE EXCEPTION message so operators can see
-- which endpoint was returning 4xx.

-- ── 1. Persistent audit table ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.batch_http_log (
  request_id   bigint      PRIMARY KEY,
  url          text        NOT NULL,
  enqueued_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS batch_http_log_enqueued_at_idx
  ON public.batch_http_log (enqueued_at);

COMMENT ON TABLE public.batch_http_log IS
  'Audit log of /batch/* HTTP requests submitted via net.http_post. '
  'Populated by trg_capture_batch_http_request before pg_net GC removes '
  'the corresponding net.http_request_queue row. Pruned to 7 days by '
  'cron_assert_no_recent_pg_net_batch_http_4xx on each watcher run.';

-- ── 2. Trigger function: capture /batch/* URL at enqueue time ────────

CREATE OR REPLACE FUNCTION public._capture_batch_http_request()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = net, public
AS $$
BEGIN
  IF NEW.url ILIKE '%/batch/%' THEN
    INSERT INTO public.batch_http_log (request_id, url, enqueued_at)
    VALUES (NEW.id, NEW.url, now())
    ON CONFLICT (request_id) DO NOTHING;
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public._capture_batch_http_request() IS
  'Trigger body: persists /batch/* request (id, url) into batch_http_log '
  'immediately on net.http_request_queue insert, before pg_net GC.';

-- ── 3. Trigger on net.http_request_queue ────────────────────────────

DROP TRIGGER IF EXISTS trg_capture_batch_http_request ON net.http_request_queue;
CREATE TRIGGER trg_capture_batch_http_request
  AFTER INSERT ON net.http_request_queue
  FOR EACH ROW EXECUTE FUNCTION public._capture_batch_http_request();

-- ── 4. Pruning helper ────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public._prune_batch_http_log()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  DELETE FROM public.batch_http_log WHERE enqueued_at < now() - interval '7 days';
$$;

COMMENT ON FUNCTION public._prune_batch_http_log() IS
  'Deletes batch_http_log rows older than 7 days. Called inline from '
  'cron_assert_no_recent_pg_net_batch_http_4xx on every watcher run.';

-- ── 5. Updated admin RPC: join to batch_http_log ────────────────────

CREATE OR REPLACE FUNCTION public.admin_pg_net_batch_http_4xx_events(p_hours int DEFAULT 6)
RETURNS TABLE (
  response_id  bigint,
  status_code  int,
  created_at   timestamptz,
  request_url  text
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
    l.url
  FROM net._http_response r
  JOIN public.batch_http_log l ON l.request_id = r.id
  WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
    AND r.status_code >= 400
    AND r.status_code < 500
  ORDER BY r.created DESC;
$$;

REVOKE ALL ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) TO service_role;

COMMENT ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) IS
  'Returns recent /batch/* pg_net 4xx responses joined to batch_http_log '
  '(survives past http_request_queue GC). Admin alert + debugging use.';

-- ── 6. Updated watcher: join to batch_http_log, include URL in alert ─

CREATE OR REPLACE FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(p_hours int DEFAULT 3)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = net, public
AS $$
DECLARE
  n      int;
  sample text;
BEGIN
  -- Opportunistic prune on every watcher run (no separate cron needed).
  PERFORM public._prune_batch_http_log();

  SELECT count(*)::int INTO n
  FROM net._http_response r
  JOIN public.batch_http_log l ON l.request_id = r.id
  WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
    AND r.status_code >= 400
    AND r.status_code < 500;

  IF n > 0 THEN
    SELECT string_agg(
      format('%s %s @ %s', r.status_code::text, l.url, left(r.created::text, 19)),
      ' | '
      ORDER BY r.created DESC
    ) INTO sample
    FROM (
      SELECT r.status_code, r.created, l.url
      FROM net._http_response r
      JOIN public.batch_http_log l ON l.request_id = r.id
      WHERE r.created >= now() - make_interval(hours => greatest(1, p_hours))
        AND r.status_code >= 400
        AND r.status_code < 500
      ORDER BY r.created DESC
      LIMIT 5
    ) r;

    RAISE EXCEPTION
      USING message = format(
        'pg_net: %s batch HTTP 4xx in last %s h — sample: %s',
        n, p_hours, sample
      );
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) TO postgres;

COMMENT ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) IS
  'pg_cron watcher: raises if any /batch/* net._http_response row in the '
  'past p_hours hours has status_code 4xx, joined via batch_http_log '
  '(survives past http_request_queue GC). URL included in the error message.';
