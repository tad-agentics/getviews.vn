-- Comment sentiment radar — per-video aggregate of comment sentiment, purchase
-- intent, question rate, and audience language skew.
--
-- Design: artifacts/docs/features/comment-sentiment.md
-- Module: cloud-run/getviews_pipeline/comment_radar.py
--
-- Cached for 7 days (see is_comment_radar_fresh in pipelines); fetched on
-- demand for paid intents (video_diagnosis, creator_search best_video) to
-- keep EnsembleData unit cost bounded.

ALTER TABLE video_corpus
  ADD COLUMN comment_radar            JSONB,
  ADD COLUMN comment_radar_fetched_at TIMESTAMPTZ;

CREATE INDEX video_corpus_comment_radar_fetched_idx
  ON video_corpus (comment_radar_fetched_at DESC NULLS LAST)
  WHERE comment_radar IS NOT NULL;

COMMENT ON COLUMN video_corpus.comment_radar IS
  'CommentRadar.asdict() — sentiment pcts, purchase_intent {count,top_phrases}, '
  'questions_asked, language. Fetched on demand, 7-day TTL.';
COMMENT ON COLUMN video_corpus.comment_radar_fetched_at IS
  'Timestamp of the EnsembleData /tt/post/comments fetch that produced the '
  'current comment_radar. Rows older than 7 days are refetched.';
