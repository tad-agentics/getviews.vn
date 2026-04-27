-- Thumbnail / cover-frame analysis — Gemini's read on why the video's first
-- frame stops the scroll (or doesn't).
--
-- Design: artifacts/docs/features/thumbnail-analysis.md
-- Module: cloud-run/getviews_pipeline/thumbnail_analysis.py
--
-- Per-video output: {stop_power_score, dominant_element, text_on_thumbnail,
-- facial_expression, colour_contrast, why_it_stops}. Cached for 30 days
-- (thumbnails change less often than comment sentiment); refetched when
-- a creator re-submits the same video after making a thumbnail edit.

ALTER TABLE video_corpus
  ADD COLUMN thumbnail_analysis            JSONB,
  ADD COLUMN thumbnail_analysis_fetched_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS video_corpus_thumbnail_fetched_idx
  ON video_corpus (thumbnail_analysis_fetched_at DESC NULLS LAST)
  WHERE thumbnail_analysis IS NOT NULL;

COMMENT ON COLUMN video_corpus.thumbnail_analysis IS
  'ThumbnailAnalysis.asdict() — stop_power_score (0-10), dominant_element, '
  'text_on_thumbnail, facial_expression, colour_contrast, why_it_stops. '
  'Produced by a Gemini image call on frame-0. 30-day TTL.';
COMMENT ON COLUMN video_corpus.thumbnail_analysis_fetched_at IS
  'Timestamp of the Gemini thumbnail analysis that produced the current '
  'thumbnail_analysis payload. Rows older than 30 days are refetched.';
