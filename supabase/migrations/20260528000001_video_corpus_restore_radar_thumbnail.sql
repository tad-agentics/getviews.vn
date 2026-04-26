-- Restore comment_radar + thumbnail_analysis cache columns after
-- 20260426030832_hosted_hotfix_orphan_fks_and_corpus_cleanup (prod hotfix).
-- Idempotent: safe if columns already exist (e.g. fresh replay after 26030832).

ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS comment_radar JSONB,
  ADD COLUMN IF NOT EXISTS comment_radar_fetched_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS thumbnail_analysis JSONB,
  ADD COLUMN IF NOT EXISTS thumbnail_analysis_fetched_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS video_corpus_comment_radar_fetched_idx
  ON public.video_corpus (comment_radar_fetched_at DESC NULLS LAST)
  WHERE comment_radar IS NOT NULL;

CREATE INDEX IF NOT EXISTS video_corpus_thumbnail_fetched_idx
  ON public.video_corpus (thumbnail_analysis_fetched_at DESC NULLS LAST)
  WHERE thumbnail_analysis IS NOT NULL;

COMMENT ON COLUMN public.video_corpus.comment_radar IS
  'CommentRadar payload; see 20260421000047_video_corpus_comment_radar.sql.';
COMMENT ON COLUMN public.video_corpus.comment_radar_fetched_at IS
  'When comment_radar was fetched; TTL ~7d in pipeline.';
COMMENT ON COLUMN public.video_corpus.thumbnail_analysis IS
  'ThumbnailAnalysis JSON; see 20260422000048_video_corpus_thumbnail_analysis.sql.';
COMMENT ON COLUMN public.video_corpus.thumbnail_analysis_fetched_at IS
  'When thumbnail_analysis was fetched; TTL ~30d in pipeline.';
