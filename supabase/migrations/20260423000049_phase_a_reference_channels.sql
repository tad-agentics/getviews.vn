-- Phase A · A1 — reference channels + starter creators + auto-seed.
--
-- The design's onboarding step 2 asks the user to pick 1–3 "kênh tham chiếu"
-- (reference channels). Those handles become the creator's peer set: every
-- home/pulse/morning-ritual signal is anchored to what those peers are doing
-- this week, not to a global niche average.
--
-- Shipping shape:
--   - profiles.reference_channel_handles — 0–3 handles the user tracks
--   - starter_creators — a pool of curatable starter suggestions per niche,
--     seeded from the top-follower creators already sitting in video_corpus
--   - RPC `seed_starter_creators` — one-shot function the ops dashboard or a
--     migration can invoke to (re)populate the pool from corpus aggregates
--
-- See artifacts/docs/home-api.md for consumption.

-- ── profiles.reference_channel_handles ────────────────────────────────────
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS reference_channel_handles TEXT[] NOT NULL DEFAULT '{}'
    CHECK (cardinality(reference_channel_handles) <= 3);

CREATE INDEX IF NOT EXISTS idx_profiles_reference_channel_handles
  ON profiles USING GIN (reference_channel_handles);

-- ── starter_creators ──────────────────────────────────────────────────────
-- followers / avg_views are BIGINT to match video_corpus.creator_followers
-- (BIGINT since migration 0020) and video_corpus.views (BIGINT since 0005).
CREATE TABLE IF NOT EXISTS starter_creators (
  niche_id         INTEGER NOT NULL REFERENCES niche_taxonomy (id) ON DELETE CASCADE,
  handle           TEXT    NOT NULL,
  display_name     TEXT,
  followers        BIGINT  NOT NULL DEFAULT 0,
  avg_views        BIGINT  NOT NULL DEFAULT 0,
  video_count      INTEGER NOT NULL DEFAULT 0,
  is_curated       BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE once a human edits the row
  rank             INTEGER NOT NULL DEFAULT 0,      -- 1 = most prominent in niche
  last_seeded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (niche_id, handle)
);

CREATE INDEX idx_starter_creators_niche_rank
  ON starter_creators (niche_id, rank);

ALTER TABLE starter_creators ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users read starter_creators"
  ON starter_creators FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

-- ── seed_starter_creators() ───────────────────────────────────────────────
-- Rebuild the pool from video_corpus. Keeps any human-curated rows
-- (is_curated = TRUE) intact — only overwrites auto-seeded rows. Safe to
-- re-run after new ingests.
CREATE OR REPLACE FUNCTION seed_starter_creators(p_top_n INTEGER DEFAULT 10)
RETURNS TABLE (out_niche_id INTEGER, out_seeded INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Recompute aggregate per (niche_id, creator_handle); rank within niche.
  RETURN QUERY
  WITH ranked AS (
    SELECT
      v.niche_id                                                     AS r_niche_id,
      v.creator_handle                                               AS handle,
      MAX(COALESCE(v.creator_followers, 0))                         AS followers,
      AVG(COALESCE(v.views, 0))::BIGINT                              AS avg_views,
      COUNT(*)::INT                                                  AS video_count,
      ROW_NUMBER() OVER (
        PARTITION BY v.niche_id
        ORDER BY MAX(COALESCE(v.creator_followers, 0)) DESC, COUNT(*) DESC
      )                                                              AS rk
    FROM video_corpus v
    WHERE v.creator_handle IS NOT NULL AND v.creator_handle <> ''
    GROUP BY v.niche_id, v.creator_handle
  ),
  touched AS (
    INSERT INTO starter_creators (
      niche_id, handle, display_name, followers, avg_views,
      video_count, is_curated, rank, last_seeded_at
    )
    SELECT r.r_niche_id, r.handle, NULL, r.followers, r.avg_views,
           r.video_count, FALSE, r.rk::INT, now()
    FROM ranked r
    WHERE r.rk <= p_top_n
    ON CONFLICT (niche_id, handle) DO UPDATE
      SET followers      = EXCLUDED.followers,
          avg_views      = EXCLUDED.avg_views,
          video_count    = EXCLUDED.video_count,
          rank           = EXCLUDED.rank,
          last_seeded_at = now()
      -- Don't clobber a human edit.
      WHERE starter_creators.is_curated = FALSE
    RETURNING starter_creators.niche_id AS t_niche_id
  )
  SELECT t.t_niche_id, COUNT(*)::INT FROM touched t GROUP BY t.t_niche_id;
END;
$$;

REVOKE ALL ON FUNCTION seed_starter_creators(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION seed_starter_creators(INTEGER) TO service_role;

-- One-shot initial seed. Safe to drop/re-run manually later.
SELECT seed_starter_creators(10);
