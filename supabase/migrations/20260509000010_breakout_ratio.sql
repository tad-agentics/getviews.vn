-- Lightreel parity: pre-store breakout_ratio (views / creator_median_views)
-- at ingest time so reports can filter "only breakout videos" efficiently
-- without a join or subquery at query time.
-- creator_median_views is also stored so the ratio can be recomputed
-- if views are updated on a backfill pass.

ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS breakout_ratio   NUMERIC(12, 2),
  ADD COLUMN IF NOT EXISTS creator_median_views BIGINT;

CREATE INDEX IF NOT EXISTS idx_corpus_breakout_ratio
  ON public.video_corpus (niche_id, breakout_ratio DESC)
  WHERE breakout_ratio IS NOT NULL;

COMMENT ON COLUMN public.video_corpus.breakout_ratio IS
  'views / creator_median_views at time of ingest. >5 = breakout, >20 = viral. NULL until backfill or new ingest.';
COMMENT ON COLUMN public.video_corpus.creator_median_views IS
  'Median views of creator''s last 30 posts at time of ingest (from EnsembleData stats).';
