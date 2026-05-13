-- Admin-only RPC: flush cached video_diagnostics for a specific TikTok URL.
-- Used by the acceptance test beforeAll to ensure a fresh v5 analysis is run.
-- Security: SECURITY DEFINER runs as postgres, but checks profiles.is_admin first.

CREATE OR REPLACE FUNCTION admin_flush_video_diagnostics_cache(
  p_tiktok_url TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_is_admin BOOLEAN;
  v_deleted  INT;
BEGIN
  -- Gate: caller must be an admin.
  SELECT COALESCE(is_admin, false)
    INTO v_is_admin
    FROM profiles
   WHERE id = auth.uid();

  IF NOT FOUND OR NOT v_is_admin THEN
    RAISE EXCEPTION 'Not authorized — admin only' USING ERRCODE = '42501';
  END IF;

  -- Delete all video_diagnostics rows whose tiktok_url contains the video ID
  -- from the supplied URL (handles URL variants: http/https, www, query params).
  WITH extracted AS (
    -- Extract the numeric video ID from the URL (last path segment of digits).
    SELECT (regexp_match(p_tiktok_url, '/(\d{15,20})'))[1] AS video_id
  ),
  deleted AS (
    DELETE FROM video_diagnostics vd
    USING extracted ex
    WHERE ex.video_id IS NOT NULL
      AND vd.tiktok_url ILIKE ('%' || ex.video_id || '%')
    RETURNING vd.id
  )
  SELECT count(*) INTO v_deleted FROM deleted;

  RETURN jsonb_build_object(
    'ok',      true,
    'deleted', v_deleted,
    'url',     p_tiktok_url
  );
END;
$$;

-- Grant to authenticated role (RPC called with user JWT via Supabase JS client).
GRANT EXECUTE ON FUNCTION admin_flush_video_diagnostics_cache(TEXT) TO authenticated;

COMMENT ON FUNCTION admin_flush_video_diagnostics_cache(TEXT) IS
  'Flush the on-demand video_diagnostics cache for a specific TikTok URL.
   Admin-only (profiles.is_admin required). Used by acceptance tests to force
   a fresh v5 analysis instead of getting a stale v4 cached response.';
