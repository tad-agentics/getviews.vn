-- 2026-05-09 — add last_refetched_at to video_corpus for freshness tracking.
--
-- Closes the Axis 3 gap in state-of-corpus.md: today every row in
-- video_corpus carries stats (views, likes, comments, shares, saves,
-- engagement_rate, save_rate) frozen at ingest time and never
-- refreshed. A video that went viral post-ingest is invisible to our
-- breakout detection and lifecycle scoring.
--
-- This column records the last time a row's metrics were re-pulled
-- from EnsembleData. NULL means "never refreshed" — the daily refresh
-- cron prioritises NULLs first, then stale-by-age, both filtered by a
-- views threshold so we don't burn ED quota on low-signal tails.
--
-- Writer: cloud-run/getviews_pipeline/corpus_refresh.py (new, same
-- commit). Reader: same module's _select_refresh_candidates query.

ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS last_refetched_at TIMESTAMPTZ;

-- "Which rows need refreshing next?" — NULLs first, then oldest.
-- Scoped to views >= 1000 via the application query so the partial
-- index on high-views rows pays off; we don't add a partial index
-- here because the views threshold is configuration, not a constant.
CREATE INDEX IF NOT EXISTS video_corpus_last_refetched_at_idx
  ON public.video_corpus (last_refetched_at NULLS FIRST, views DESC);

COMMENT ON COLUMN public.video_corpus.last_refetched_at IS
  'When stats (views/likes/comments/shares/saves) were last refreshed from EnsembleData. NULL = never refreshed since ingest.';
