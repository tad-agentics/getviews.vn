-- Fix admin_flush_video_diagnostics_cache: video_diagnostics has no ``id`` column
-- (PK is video_id). Also match by video_id directly for rows with NULL tiktok_url.

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
  SELECT COALESCE(is_admin, false)
    INTO v_is_admin
    FROM profiles
   WHERE id = auth.uid();

  IF NOT FOUND OR NOT v_is_admin THEN
    RAISE EXCEPTION 'Not authorized — admin only' USING ERRCODE = '42501';
  END IF;

  WITH extracted AS (
    SELECT (regexp_match(p_tiktok_url, '/(\d{15,22})'))[1] AS video_id
  ),
  deleted AS (
    DELETE FROM video_diagnostics vd
    USING extracted ex
    WHERE ex.video_id IS NOT NULL
      AND (
        vd.video_id = ex.video_id
        OR vd.tiktok_url ILIKE ('%' || ex.video_id || '%')
      )
    RETURNING vd.video_id
  )
  SELECT count(*) INTO v_deleted FROM deleted;

  RETURN jsonb_build_object(
    'ok',      true,
    'deleted', v_deleted,
    'url',     p_tiktok_url
  );
END;
$$;
