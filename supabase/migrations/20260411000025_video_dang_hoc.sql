-- P2-12: Video Đáng Học — daily rankings (Bùng Nổ / Đang Hot)

CREATE TABLE IF NOT EXISTS video_dang_hoc (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id TEXT NOT NULL,
  list_type TEXT NOT NULL CHECK (list_type IN ('bung_no', 'dang_hot')),
  rank INTEGER NOT NULL,
  breakout_multiplier FLOAT,
  velocity FLOAT,
  refreshed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (video_id, list_type)
);

CREATE INDEX IF NOT EXISTS idx_video_dang_hoc_list_rank ON video_dang_hoc (list_type, rank);

ALTER TABLE video_dang_hoc ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "video_dang_hoc_select" ON video_dang_hoc;
CREATE POLICY "video_dang_hoc_select"
  ON video_dang_hoc FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "video_dang_hoc_service" ON video_dang_hoc;
CREATE POLICY "video_dang_hoc_service"
  ON video_dang_hoc FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
