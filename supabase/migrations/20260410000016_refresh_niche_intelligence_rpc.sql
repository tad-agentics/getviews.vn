-- RPC: refresh_niche_intelligence
-- Called by Cloud Run batch ingest after each corpus update.
-- Uses SECURITY DEFINER so it runs as the function owner (service_role),
-- which has the necessary privilege to REFRESH MATERIALIZED VIEW.

CREATE OR REPLACE FUNCTION refresh_niche_intelligence()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY niche_intelligence;
END;
$$;

-- Only service_role (Cloud Run) should call this — not anon or authenticated clients.
REVOKE EXECUTE ON FUNCTION refresh_niche_intelligence() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION refresh_niche_intelligence() FROM anon;
REVOKE EXECUTE ON FUNCTION refresh_niche_intelligence() FROM authenticated;
GRANT EXECUTE ON FUNCTION refresh_niche_intelligence() TO service_role;
