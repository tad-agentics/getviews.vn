-- 2026-06-03 — D1 — Kho Douyin · per-scene shot table.
--
-- Mirrors ``video_shots`` (the Vietnamese TikTok per-scene descriptor
-- table) for the Douyin pipeline. Used by the D2 ingest dual-write
-- path: each scene from the Gemini analysis (analysis_json.scenes[])
-- gets projected here for fast matcher lookup, plus an R2-hosted JPG
-- frame URL.
--
-- Why a separate table (not extending video_shots with platform col):
--   - FK to a different parent table (douyin_video_corpus) — enforcing
--     referential integrity is cleaner per-platform.
--   - The shot-reference matcher (Wave 2.5 PR #5) hard-filters by
--     niche_id; Douyin niches live in douyin_niche_taxonomy, not
--     niche_taxonomy, so any cross-platform query would already have
--     to UNION the two trees anyway.
--   - Scene enrichment dimensions (framing/pace/etc.) are platform-
--     agnostic so the column shape mirrors video_shots exactly.
--
-- Writer: D2 ingest pipeline via service-role (mirrors the
-- ``video_shots_writer.build_video_shot_rows`` pattern).

CREATE TABLE IF NOT EXISTS douyin_video_shots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id TEXT NOT NULL,
  niche_id INTEGER NOT NULL,
  scene_index INTEGER NOT NULL,
  start_s REAL,
  end_s REAL,

  -- Legacy 4-value taxonomy (face_to_camera | product_shot | demo | action).
  -- Kept for back-compat with the matcher; Gemini may emit either this OR
  -- the enriched dimensions below.
  scene_type TEXT,

  -- Enriched descriptors (Wave 2.5 PR #2 — Gemini extraction). All optional;
  -- the matcher null-tolerates missing fields.
  framing TEXT,
  pace TEXT,
  overlay_style TEXT,
  subject TEXT,
  motion TEXT,
  description TEXT,

  -- Denormalized from douyin_video_corpus at write time (matcher's lookup
  -- query stays join-free; mirror of video_shots' denormalization).
  hook_type TEXT,
  creator_handle TEXT,
  thumbnail_url TEXT,
  douyin_url TEXT,

  -- Per-scene representative frame on R2.
  frame_url TEXT,

  -- Denormalized for the FE RefClipCard "X view" chip (mirrors PR S2
  -- where we added ``views`` to ``video_shots``).
  views BIGINT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT douyin_video_shots_video_fk
    FOREIGN KEY (video_id) REFERENCES public.douyin_video_corpus(video_id)
    ON DELETE CASCADE,

  CONSTRAINT douyin_video_shots_video_scene_unique
    UNIQUE (video_id, scene_index),

  CONSTRAINT douyin_video_shots_scene_index_nonneg CHECK (scene_index >= 0),
  CONSTRAINT douyin_video_shots_start_end_valid
    CHECK (start_s IS NULL OR end_s IS NULL OR start_s <= end_s)
);

-- Hot matcher lookup (mirrors video_shots_match_idx).
CREATE INDEX IF NOT EXISTS idx_douyin_shots_match
  ON douyin_video_shots (niche_id, framing, pace, overlay_style);

CREATE INDEX IF NOT EXISTS idx_douyin_shots_niche_hook
  ON douyin_video_shots (niche_id, hook_type)
  WHERE hook_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_douyin_shots_video_idx
  ON douyin_video_shots (video_id, scene_index);

ALTER TABLE douyin_video_shots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read douyin_video_shots"
  ON douyin_video_shots FOR SELECT
  TO authenticated
  USING (true);

COMMENT ON TABLE douyin_video_shots IS
  'D1 (2026-06-03) — per-scene enriched descriptors for Douyin videos. Mirrors video_shots (TikTok). Writer: D2 ingest dual-write path via service-role.';
