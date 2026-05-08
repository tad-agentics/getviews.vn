-- pg_net: detect silent batch HTTP 4xx from pg_cron → Cloud Run /batch/* calls.
--
-- When Vault ``cloud_run_api_url`` points at the **user** pod instead of the
-- **batch** pod, ``net.http_post`` still "succeeds" from pg_cron's perspective
-- (job_run_details shows success) while ``net._http_response.status_code`` is
-- 401/404. This migration adds:
--   1. RPC ``admin_pg_net_batch_http_4xx_events`` for the admin alert evaluator.
--   2. Assert helper + hourly pg_cron that **fails** the job row if any 4xx
--      rows match a ``/batch/`` request URL (when the request row still exists
--      in ``net.http_request_queue`` — typical for recent async completes).
--   3. ``admin_alert_rules`` row ``pg_net_batch_http_4xx`` (Slack via existing
--      admin alert sweep).
--
-- Ops: Vault must hold the **batch** service base URL in ``cloud_run_api_url``
-- (same origin that serves ``POST /batch/*``) and ``cloud_run_batch_secret``
-- equal to ``BATCH_SECRET`` on the batch Cloud Run service. Verify in SQL:
--
--   SELECT name,
--          length(decrypted_secret::text) AS len,
--          left(decrypted_secret::text, 60) AS preview
--   FROM vault.decrypted_secrets
--   WHERE name IN ('cloud_run_api_url', 'cloud_run_batch_secret');
--
-- Expect ``cloud_run_api_url`` preview to match the batch hostname (often
-- includes ``batch``). If it matches the user-only service, repoint Vault then
-- spot-check recent pg_net rows joined to the request queue (URLs + status).
-- Note: the join only sees rows while ``net.http_request_queue`` still holds
-- the request id; use ``POST /batch/ping`` (batch pod) for a live smoke test.

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
    AND r.status_code < 500
    AND q.url ILIKE '%/batch/%';
$$;

REVOKE ALL ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) TO service_role;

COMMENT ON FUNCTION public.admin_pg_net_batch_http_4xx_events(int) IS
  'Returns recent pg_net HTTP 4xx rows whose request URL targets /batch/* (admin alert + debugging).';


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
    AND r.status_code < 500
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
        AND r.status_code < 500
        AND q.url ILIKE '%/batch/%'
      ORDER BY r.created DESC
      LIMIT 5
    ) r;

    RAISE EXCEPTION
      USING message = format(
        'pg_net: %s batch HTTP 4xx in last %s h (status@time sample): %s',
        n, p_hours, sample
      );
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) TO postgres;

COMMENT ON FUNCTION public.cron_assert_no_recent_pg_net_batch_http_4xx(int) IS
  'pg_cron helper: raises if recent /batch/* pg_net calls returned HTTP 4xx.';


-- Idempotent (re-apply safe): drop job name then reschedule.
SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname = 'cron-pg-net-batch-http-4xx-watch';

SELECT cron.schedule(
  'cron-pg-net-batch-http-4xx-watch',
  '23 * * * *',
  $cmd$SELECT public.cron_assert_no_recent_pg_net_batch_http_4xx(3)$cmd$
);

INSERT INTO public.admin_alert_rules (rule_key, label, severity, threshold_json)
VALUES (
  'pg_net_batch_http_4xx',
  'pg_cron → batch: HTTP 4xx trong cửa sổ gần đây (net._http_response)',
  'warn',
  '{"max_4xx": 0, "hours": 6}'::jsonb
)
ON CONFLICT (rule_key) DO NOTHING;
