-- 2026-06-16 — Douyin playback + two-axis content_class on douyin_video_corpus.
--
-- playback_url: permanent R2 public URL (videos/{aweme_id}.mp4) for in-app
--   study — unlike ephemeral play_addr CDN links.
-- content_class_id / content_format: HI-9 + junction resolution for reference
--   pool matching (Phase 2a). Flat niche_id remains for Kho Douyin UI chips.

ALTER TABLE douyin_video_corpus
  ADD COLUMN IF NOT EXISTS playback_url TEXT,
  ADD COLUMN IF NOT EXISTS content_class_id INTEGER,
  ADD COLUMN IF NOT EXISTS content_format TEXT;

CREATE INDEX IF NOT EXISTS idx_douyin_corpus_content_class
  ON douyin_video_corpus (content_class_id, views DESC)
  WHERE content_class_id IS NOT NULL;

COMMENT ON COLUMN douyin_video_corpus.playback_url IS
  'Permanent R2 MP4 URL for in-app playback (standard play_addr banked at ingest). NULL until banking runs.';

COMMENT ON COLUMN douyin_video_corpus.content_class_id IS
  'Two-axis content class from HI-9 niche_classification + junction (Phase 2a). Used for reference pool matching.';

COMMENT ON COLUMN douyin_video_corpus.content_format IS
  'format_axis or carousel_format_axis from extraction — denormalized for display/filter.';
